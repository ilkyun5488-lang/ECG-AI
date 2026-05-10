"""MIT-BIH 부정맥 데이터셋을 딥러닝 학습용 심박 단위 데이터로 전처리합니다."""

from collections import Counter
from pathlib import Path
import csv
import json
import os
import platform
import random
import sys
import zipfile

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

try:
    import wfdb
except ImportError as exc:
    raise SystemExit(
        "wfdb 라이브러리가 설치되어 있지 않습니다.\n"
        "터미널에서 아래 명령어를 먼저 실행해 주세요.\n\n"
        "pip install wfdb matplotlib numpy"
    ) from exc


# 운영체제에 따라 한글 폰트 자동 설정
if platform.system() == "Windows":
    plt.rcParams["font.family"] = "Malgun Gothic"
elif platform.system() == "Darwin":  # macOS
    plt.rcParams["font.family"] = "AppleGothic"
else:  # Linux
    plt.rcParams["font.family"] = "NanumGothic"

plt.rcParams["axes.unicode_minus"] = False  # 마이너스 기호 깨짐 방지

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


BASE_DIR = Path(__file__).resolve().parent
ZIP_PATH = Path(
    os.environ.get(
        "MIT_BIH_ZIP_PATH",
        BASE_DIR.parent / "data" / "mit-bih-arrhythmia-database-1.0.0.zip",
    )
)
EXTRACT_DIR = ZIP_PATH.with_suffix("")
OUTPUT_DIR = ZIP_PATH.parent / "mit_bih_preprocessed"

# R-peak를 기준으로 앞 0.2초, 뒤 0.4초를 잘라 한 개의 심박 샘플로 만듭니다.
PRE_R_SECONDS = 0.2
POST_R_SECONDS = 0.4

# 처음에는 정상, PAC, PVC를 중심으로 작게 시작합니다.
# 나중에 다른 annotation symbol을 추가하고 싶으면 이 사전에 항목을 더 넣으면 됩니다.
LABEL_MAP = {
    "N": 0,  # Normal beat, 정상 박동
    "A": 1,  # Atrial premature beat, PAC
    "V": 2,  # Premature ventricular contraction, PVC
}

LABEL_DESCRIPTION = {
    "N": "정상 박동",
    "A": "PAC, 심방조기수축",
    "V": "PVC, 심실조기수축",
}

TEST_RATIO = 0.2
RANDOM_SEED = 42
PREFERRED_LEAD = "MLII"
INCLUDE_X_RECORDS = False


def extract_zip_if_needed(zip_path: Path, extract_dir: Path) -> None:
    """압축이 아직 풀려 있지 않으면 zip 파일을 해제합니다."""
    if not zip_path.exists():
        raise FileNotFoundError(f"압축파일을 찾을 수 없습니다: {zip_path}")

    if extract_dir.exists() and any(extract_dir.rglob("*.hea")):
        print(f"이미 압축이 풀려 있습니다: {extract_dir}")
        return

    print(f"압축을 해제합니다: {zip_path}")
    with zipfile.ZipFile(zip_path, "r") as zip_file:
        zip_file.extractall(zip_path.parent)
    print(f"압축 해제 완료: {extract_dir}")


def find_complete_records(extract_dir: Path) -> list[Path]:
    """dat, hea, atr 파일이 모두 있는 record 목록을 찾습니다."""
    record_bases: list[Path] = []

    for hea_path in sorted(extract_dir.rglob("*.hea")):
        record_base = hea_path.with_suffix("")
        if not INCLUDE_X_RECORDS and record_base.name.startswith("x_"):
            continue
        if record_base.with_suffix(".dat").exists() and record_base.with_suffix(".atr").exists():
            record_bases.append(record_base)

    if not record_bases:
        raise FileNotFoundError(".dat, .hea, .atr 파일이 모두 있는 record를 찾지 못했습니다.")

    return record_bases


def choose_signal_channel(record) -> int:
    """가능하면 MLII lead를 사용하고, 없으면 첫 번째 채널을 사용합니다."""
    if PREFERRED_LEAD in record.sig_name:
        return record.sig_name.index(PREFERRED_LEAD)
    return 0


def normalize_to_0_1(beat: np.ndarray) -> np.ndarray:
    """심박 조각의 전압 값을 0~1 범위로 정규화합니다."""
    min_value = float(np.min(beat))
    max_value = float(np.max(beat))

    if np.isclose(max_value, min_value):
        return np.zeros_like(beat, dtype=np.float32)

    return ((beat - min_value) / (max_value - min_value)).astype(np.float32)


def segment_record(record_base: Path) -> tuple[list[np.ndarray], list[int], list[dict]]:
    """한 record에서 R-peak annotation을 기준으로 심박 단위 데이터를 자릅니다."""
    record = wfdb.rdrecord(str(record_base))
    annotation = wfdb.rdann(str(record_base), "atr")

    channel_idx = choose_signal_channel(record)
    signal = record.p_signal[:, channel_idx]
    lead_name = record.sig_name[channel_idx]

    pre_samples = int(round(PRE_R_SECONDS * record.fs))
    post_samples = int(round(POST_R_SECONDS * record.fs))
    expected_length = pre_samples + post_samples

    X_parts: list[np.ndarray] = []
    y_parts: list[int] = []
    metadata_rows: list[dict] = []

    for sample, symbol in zip(annotation.sample, annotation.symbol):
        if symbol not in LABEL_MAP:
            continue

        start = int(sample) - pre_samples
        end = int(sample) + post_samples

        # record 시작이나 끝에 너무 가까운 beat는 길이가 맞지 않아 제외합니다.
        if start < 0 or end > len(signal):
            continue

        beat = signal[start:end]
        if len(beat) != expected_length:
            continue

        normalized_beat = normalize_to_0_1(beat)
        X_parts.append(normalized_beat)
        y_parts.append(LABEL_MAP[symbol])
        metadata_rows.append(
            {
                "record": record_base.name,
                "symbol": symbol,
                "label": LABEL_MAP[symbol],
                "label_name": LABEL_DESCRIPTION[symbol],
                "r_peak_sample": int(sample),
                "r_peak_time_sec": round(float(sample / record.fs), 6),
                "lead": lead_name,
                "fs": float(record.fs),
                "start_sample": int(start),
                "end_sample": int(end),
            }
        )

    print(
        f"{record_base.name}: {len(X_parts):,}개 beat 추출 "
        f"(사용 lead={lead_name}, fs={record.fs}Hz)"
    )
    return X_parts, y_parts, metadata_rows


def stratified_train_test_split(
    X: np.ndarray,
    y: np.ndarray,
    metadata_rows: list[dict],
    test_ratio: float = TEST_RATIO,
    random_seed: int = RANDOM_SEED,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[dict], list[dict]]:
    """라벨 비율이 크게 깨지지 않도록 train/test를 나눕니다."""
    rng = random.Random(random_seed)
    train_indices: list[int] = []
    test_indices: list[int] = []

    for label in sorted(set(y.tolist())):
        label_indices = np.where(y == label)[0].tolist()
        rng.shuffle(label_indices)

        if len(label_indices) <= 1:
            train_indices.extend(label_indices)
            continue

        test_count = max(1, int(round(len(label_indices) * test_ratio)))
        test_indices.extend(label_indices[:test_count])
        train_indices.extend(label_indices[test_count:])

    rng.shuffle(train_indices)
    rng.shuffle(test_indices)

    train_metadata = [metadata_rows[idx] for idx in train_indices]
    test_metadata = [metadata_rows[idx] for idx in test_indices]

    return (
        X[train_indices],
        X[test_indices],
        y[train_indices],
        y[test_indices],
        train_metadata,
        test_metadata,
    )


def save_metadata_csv(path: Path, rows: list[dict]) -> None:
    """각 심박 샘플이 어느 record와 annotation에서 왔는지 CSV로 저장합니다."""
    if not rows:
        return

    with path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def save_outputs(
    X: np.ndarray,
    y: np.ndarray,
    metadata_rows: list[dict],
    output_dir: Path,
) -> None:
    """전처리 결과를 npy, json, csv 파일로 저장합니다."""
    output_dir.mkdir(parents=True, exist_ok=True)

    X_train, X_test, y_train, y_test, train_metadata, test_metadata = stratified_train_test_split(
        X, y, metadata_rows
    )

    np.save(output_dir / "X_all.npy", X)
    np.save(output_dir / "y_all.npy", y)
    np.save(output_dir / "X_train.npy", X_train)
    np.save(output_dir / "y_train.npy", y_train)
    np.save(output_dir / "X_test.npy", X_test)
    np.save(output_dir / "y_test.npy", y_test)

    save_metadata_csv(output_dir / "metadata_all.csv", metadata_rows)
    save_metadata_csv(output_dir / "metadata_train.csv", train_metadata)
    save_metadata_csv(output_dir / "metadata_test.csv", test_metadata)

    label_info = {
        "label_map": LABEL_MAP,
        "label_description": LABEL_DESCRIPTION,
        "pre_r_seconds": PRE_R_SECONDS,
        "post_r_seconds": POST_R_SECONDS,
        "normalization": "각 심박 조각마다 min-max 정규화로 0~1 범위 변환",
        "shape_meaning": "(샘플 수, 한 심박의 time step 수, 채널 수)",
        "preferred_lead": PREFERRED_LEAD,
        "include_x_records": INCLUDE_X_RECORDS,
        "test_ratio": TEST_RATIO,
        "random_seed": RANDOM_SEED,
    }
    with (output_dir / "label_map.json").open("w", encoding="utf-8") as json_file:
        json.dump(label_info, json_file, ensure_ascii=False, indent=2)

    print("\n=== 저장 완료 ===")
    print(f"저장 폴더: {output_dir}")
    print(f"X_train.npy shape: {X_train.shape}")
    print(f"y_train.npy shape: {y_train.shape}")
    print(f"X_test.npy shape: {X_test.shape}")
    print(f"y_test.npy shape: {y_test.shape}")


def print_dataset_summary(X: np.ndarray, y: np.ndarray) -> None:
    """전처리된 데이터의 크기와 라벨 분포를 한국어로 출력합니다."""
    reverse_label_map = {value: key for key, value in LABEL_MAP.items()}
    label_counts = Counter(y.tolist())

    print("\n=== 전체 전처리 데이터 요약 ===")
    print(f"X shape: {X.shape}")
    print(f"y shape: {y.shape}")
    print("라벨별 개수:")
    for label, count in sorted(label_counts.items()):
        symbol = reverse_label_map[label]
        print(f"  {label} = {symbol} ({LABEL_DESCRIPTION[symbol]}): {count:,}개")

    print(
        "\n해석: 각 X 샘플은 R-peak 앞 0.2초와 뒤 0.4초를 포함한 한 박동입니다. "
        "y는 N, A(PAC), V(PVC)를 숫자로 바꾼 라벨입니다."
    )


def main() -> None:
    """MIT-BIH 전체 record를 전처리해서 학습용 npy 파일로 저장합니다."""
    extract_zip_if_needed(ZIP_PATH, EXTRACT_DIR)
    record_bases = find_complete_records(EXTRACT_DIR)
    print(f"분석할 record 수: {len(record_bases)}개")

    X_parts: list[np.ndarray] = []
    y_parts: list[int] = []
    metadata_rows: list[dict] = []

    for record_base in record_bases:
        record_X, record_y, record_metadata = segment_record(record_base)
        X_parts.extend(record_X)
        y_parts.extend(record_y)
        metadata_rows.extend(record_metadata)

    if not X_parts:
        raise RuntimeError("전처리된 심박 데이터가 없습니다. LABEL_MAP 또는 annotation을 확인해 주세요.")

    # Conv1D 딥러닝 모델에서 바로 쓰기 쉽도록 마지막 차원에 채널 1개를 추가합니다.
    X = np.asarray(X_parts, dtype=np.float32)[..., np.newaxis]
    y = np.asarray(y_parts, dtype=np.int64)

    print_dataset_summary(X, y)
    save_outputs(X, y, metadata_rows, OUTPUT_DIR)


if __name__ == "__main__":
    main()
