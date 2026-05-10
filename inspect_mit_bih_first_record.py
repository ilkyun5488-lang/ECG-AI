"""MIT-BIH 부정맥 데이터셋의 첫 번째 record를 확인하는 예제 코드."""

from collections import Counter
from pathlib import Path
import os
import platform
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
PLOT_SECONDS = 10


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


def find_first_complete_record(extract_dir: Path) -> Path:
    """dat, hea, atr 파일이 모두 있는 첫 번째 record의 기본 경로를 찾습니다."""
    hea_files = sorted(extract_dir.rglob("*.hea"))
    if not hea_files:
        raise FileNotFoundError(f".hea 파일을 찾을 수 없습니다: {extract_dir}")

    for hea_path in hea_files:
        record_base = hea_path.with_suffix("")
        dat_path = record_base.with_suffix(".dat")
        atr_path = record_base.with_suffix(".atr")
        if dat_path.exists() and atr_path.exists():
            return record_base

    raise FileNotFoundError(".dat, .hea, .atr 파일이 모두 있는 record를 찾지 못했습니다.")


def print_record_summary(record_base: Path, record, annotation) -> None:
    """record와 annotation의 핵심 정보를 한국어로 출력합니다."""
    print("\n=== 첫 번째 MIT-BIH record 정보 ===")
    print(f"Record 이름: {record_base.name}")
    print(f"Record 위치: {record_base}")
    print(f"샘플링 주파수: {record.fs} Hz")
    print(f"전체 샘플 수: {record.sig_len:,}")
    print(f"전체 길이: {record.sig_len / record.fs:.1f}초")
    print(f"신호 채널 수: {record.n_sig}")
    print(f"채널 이름: {', '.join(record.sig_name)}")

    print("\n=== Annotation 정보 ===")
    print(f"Annotation 파일 종류: atr")
    print(f"Annotation 개수: {len(annotation.sample):,}")

    symbol_counts = Counter(annotation.symbol)
    print("\nAnnotation symbol 빈도:")
    for symbol, count in symbol_counts.most_common():
        print(f"  {symbol}: {count:,}개")

    print("\n처음 20개 annotation:")
    for idx, (sample, symbol) in enumerate(zip(annotation.sample[:20], annotation.symbol[:20]), 1):
        time_sec = sample / record.fs
        aux_note = annotation.aux_note[idx - 1].strip() if annotation.aux_note else ""
        aux_text = f", 보조정보={aux_note}" if aux_note else ""
        print(f"  {idx:02d}. sample={sample}, 시간={time_sec:.3f}초, symbol={symbol}{aux_text}")

    print(
        "\n해석: MIT-BIH annotation symbol은 각 박동 또는 리듬 사건을 표시합니다. "
        "예를 들어 N은 정상 박동, V는 PVC 같은 심실성 조기수축을 의미할 수 있습니다."
    )


def plot_first_seconds(record_base: Path, record, annotation, seconds: int = PLOT_SECONDS) -> Path:
    """첫 몇 초의 ECG 파형과 annotation 위치를 함께 그립니다."""
    sample_count = min(record.sig_len, int(record.fs * seconds))
    time_axis = np.arange(sample_count) / record.fs
    signal = record.p_signal[:sample_count, 0]
    lead_name = record.sig_name[0]

    annotation_mask = annotation.sample < sample_count
    annotation_samples = annotation.sample[annotation_mask]
    annotation_symbols = np.array(annotation.symbol, dtype=object)[annotation_mask]
    annotation_times = annotation_samples / record.fs
    annotation_values = signal[annotation_samples]

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(time_axis, signal, color="black", linewidth=1.0, label=f"{lead_name} 파형")
    ax.scatter(
        annotation_times,
        annotation_values,
        color="crimson",
        s=36,
        zorder=3,
        label="Annotation 위치",
    )

    for time_sec, value, symbol in zip(annotation_times, annotation_values, annotation_symbols):
        ax.text(time_sec, value, symbol, color="crimson", fontsize=9, ha="center", va="bottom")

    ax.set_title(f"MIT-BIH record {record_base.name}: 첫 {seconds}초 파형과 annotation")
    ax.set_xlabel("시간(초)")
    ax.set_ylabel(f"{lead_name} 진폭(mV)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right")
    fig.tight_layout()

    output_path = record_base.parent / f"{record_base.name}_first_{seconds}s_waveform.png"
    fig.savefig(output_path, dpi=160)
    if "agg" not in plt.get_backend().lower():
        plt.show()
    return output_path


def main() -> None:
    """MIT-BIH 압축 해제 후 첫 번째 record의 파형과 annotation을 확인합니다."""
    extract_zip_if_needed(ZIP_PATH, EXTRACT_DIR)
    record_base = find_first_complete_record(EXTRACT_DIR)

    # wfdb는 확장자를 제외한 record 경로를 사용합니다.
    record = wfdb.rdrecord(str(record_base))
    annotation = wfdb.rdann(str(record_base), "atr")

    print_record_summary(record_base, record, annotation)
    output_path = plot_first_seconds(record_base, record, annotation)
    print(f"\n그래프 저장 위치: {output_path}")


if __name__ == "__main__":
    main()
