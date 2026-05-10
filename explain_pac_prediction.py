"""학습된 1D-CNN 모델이 PAC로 판단한 심박을 설명하기 위한 예제 코드입니다."""

from pathlib import Path
import csv
import json
import os
import platform
import random
import sys

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

os.environ.setdefault("KERAS_BACKEND", "tensorflow")

try:
    import tensorflow as tf
    from tensorflow import keras
except ImportError as exc:
    raise SystemExit(
        "TensorFlow가 설치되어 있지 않습니다.\n"
        "모델을 학습했던 가상환경을 활성화한 뒤 실행해 주세요.\n\n"
        "예: .\\ecg_cnn_env\\Scripts\\activate\n"
        "    python explain_pac_prediction.py"
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


def resolve_data_dir() -> Path:
    """로컬과 배포 환경에서 모두 동작하도록 데이터 폴더를 찾습니다."""
    env_data_dir = os.environ.get("ECG_DATA_DIR")
    if env_data_dir:
        return Path(env_data_dir)

    candidates = [
        BASE_DIR / "data" / "mit_bih_preprocessed",
        BASE_DIR.parent / "data" / "mit_bih_preprocessed",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


DATA_DIR = resolve_data_dir()
MODEL_DIR = Path(os.environ.get("ECG_MODEL_DIR", DATA_DIR / "cnn_model"))
OUTPUT_DIR = MODEL_DIR / "explainable_pac"

PAC_LABEL = 1
NORMAL_SYMBOL = "N"
RANDOM_SEED = 42


def find_model_path(model_dir: Path) -> Path:
    """저장된 Keras 모델 파일을 찾습니다."""
    preferred_paths = [
        model_dir / "best_mit_bih_1d_cnn.keras",
        model_dir / "mit_bih_1d_cnn_final.keras",
        model_dir / "best_mit_bih_1d_cnn.h5",
        model_dir / "mit_bih_1d_cnn_final.h5",
    ]

    for path in preferred_paths:
        if path.exists():
            return path

    keras_files = sorted(model_dir.glob("*.keras")) + sorted(model_dir.glob("*.h5"))
    if keras_files:
        return keras_files[0]

    raise FileNotFoundError(
        f"학습된 모델 파일을 찾지 못했습니다: {model_dir}\n"
        "먼저 train_mit_bih_1d_cnn.py를 실행해 모델을 저장해 주세요."
    )


def load_label_info(data_dir: Path) -> tuple[dict[str, int], dict[int, str]]:
    """label_map.json을 읽어 라벨 번호와 설명을 불러옵니다."""
    with (data_dir / "label_map.json").open("r", encoding="utf-8") as json_file:
        label_info = json.load(json_file)

    symbol_to_label = {symbol: int(label) for symbol, label in label_info["label_map"].items()}
    descriptions = label_info["label_description"]
    label_to_name = {
        label: f"{symbol} ({descriptions[symbol]})"
        for symbol, label in symbol_to_label.items()
    }
    return symbol_to_label, label_to_name


def load_metadata(path: Path) -> list[dict]:
    """metadata CSV를 읽어 각 심박의 원본 정보를 불러옵니다."""
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    for row in rows:
        row["label"] = int(row["label"])
        row["r_peak_sample"] = int(row["r_peak_sample"])
        row["r_peak_time_sec"] = float(row["r_peak_time_sec"])
        row["fs"] = float(row["fs"])
        row["start_sample"] = int(row["start_sample"])
        row["end_sample"] = int(row["end_sample"])
    return rows


def load_dataset(data_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """설명에 필요한 테스트 데이터와 전체 데이터를 불러옵니다."""
    X_test = np.load(data_dir / "X_test.npy").astype(np.float32)
    y_test = np.load(data_dir / "y_test.npy").astype(np.int64)
    X_all = np.load(data_dir / "X_all.npy").astype(np.float32)
    y_all = np.load(data_dir / "y_all.npy").astype(np.int64)
    return X_test, y_test, X_all, y_all


def choose_predicted_pac_sample(
    model: keras.Model,
    X_test: np.ndarray,
    metadata_test: list[dict],
) -> tuple[int, np.ndarray, dict]:
    """테스트 데이터 중 모델이 PAC로 예측한 샘플 하나를 고릅니다."""
    probabilities = model.predict(X_test, verbose=0)
    predicted_labels = np.argmax(probabilities, axis=1)
    pac_indices = np.where(predicted_labels == PAC_LABEL)[0].tolist()

    if not pac_indices:
        raise RuntimeError("테스트 데이터에서 모델이 PAC(A)로 예측한 샘플이 없습니다.")

    rng = random.Random(RANDOM_SEED)
    selected_index = rng.choice(pac_indices)
    selected_metadata = metadata_test[selected_index]
    selected_probability = probabilities[selected_index]
    return selected_index, selected_probability, selected_metadata


def find_same_record_normal_index(
    pac_metadata: dict,
    metadata_all: list[dict],
) -> int:
    """PAC와 같은 record 안에서 가장 가까운 정상 박동의 index를 찾습니다."""
    same_record_candidates = [
        (idx, row)
        for idx, row in enumerate(metadata_all)
        if row["record"] == pac_metadata["record"] and row["symbol"] == NORMAL_SYMBOL
    ]

    if not same_record_candidates:
        raise RuntimeError(f"{pac_metadata['record']} record 안에서 정상(N) 박동을 찾지 못했습니다.")

    pac_sample = pac_metadata["r_peak_sample"]
    selected_index, _ = min(
        same_record_candidates,
        key=lambda item: abs(item[1]["r_peak_sample"] - pac_sample),
    )
    return selected_index


def calculate_previous_rr(metadata_row: dict, metadata_all: list[dict]) -> float | None:
    """해당 심박 직전 R-peak와의 RR 간격을 초 단위로 계산합니다."""
    same_record_rows = sorted(
        [row for row in metadata_all if row["record"] == metadata_row["record"]],
        key=lambda row: row["r_peak_sample"],
    )

    previous_row = None
    for row in same_record_rows:
        if row["r_peak_sample"] >= metadata_row["r_peak_sample"]:
            break
        previous_row = row

    if previous_row is None:
        return None

    return (metadata_row["r_peak_sample"] - previous_row["r_peak_sample"]) / metadata_row["fs"]


def format_rr_difference(pac_rr: float | None, normal_rr: float | None) -> str:
    """PAC RR 간격이 정상 RR 간격보다 얼마나 짧거나 긴지 문장으로 만듭니다."""
    if pac_rr is None or normal_rr is None or normal_rr == 0:
        return "RR 간격 비교 불가"

    diff_percent = (normal_rr - pac_rr) / normal_rr * 100
    if diff_percent >= 0:
        return f"정상 박동의 이전 RR보다 {diff_percent:.1f}% 짧음"
    return f"정상 박동의 이전 RR보다 {abs(diff_percent):.1f}% 김"


def summarize_pac_reason(
    pac_metadata: dict,
    normal_metadata: dict,
    pac_probability: np.ndarray,
    label_to_name: dict[int, str],
    pac_rr: float | None,
    normal_rr: float | None,
) -> str:
    """PAC로 해석하는 임상적 근거를 쉬운 문장으로 요약합니다."""
    pac_confidence = float(pac_probability[PAC_LABEL])
    rr_text = format_rr_difference(pac_rr, normal_rr)
    pac_rr_text = f"{pac_rr:.3f}초" if pac_rr is not None else "계산 불가"
    normal_rr_text = f"{normal_rr:.3f}초" if normal_rr is not None else "계산 불가"

    top_label = int(np.argmax(pac_probability))
    top_label_name = label_to_name.get(top_label, str(top_label))

    return (
        "=== PAC(A) 판독 근거 요약 ===\n"
        f"모델 최종 예측: {top_label_name}\n"
        f"PAC 예측 확률: {pac_confidence:.3f}\n"
        f"대상 record: {pac_metadata['record']}, R-peak sample: {pac_metadata['r_peak_sample']}\n"
        f"비교 정상 박동 sample: {normal_metadata['r_peak_sample']}\n"
        f"PAC 이전 RR 간격: {pac_rr_text}\n"
        f"정상 박동 이전 RR 간격: {normal_rr_text}\n"
        f"RR 비교: {rr_text}\n\n"
        "임상적 해석:\n"
        "1. PAC는 정상 박동보다 이른 시점에 심방에서 전기 신호가 먼저 발생하는 조기 수축입니다.\n"
        "2. 따라서 같은 record의 정상 박동과 비교했을 때 이전 RR 간격이 짧아지는 경향이 있습니다.\n"
        "3. 심전도에서는 QRS 앞에 조기 P파가 보이거나, P파 모양이 정상 P파와 다르게 보일 수 있습니다.\n"
        "4. P파가 T파에 겹쳐 잘 안 보이는 경우도 있어, RR 간격 변화와 QRS가 대체로 좁은지 함께 확인합니다.\n"
        "5. 이 설명은 모델 판단을 돕는 교육용 근거이며, 실제 판독은 원본 ECG와 임상 상황을 함께 봐야 합니다.\n"
    )


def plot_comparison_view(
    pac_wave: np.ndarray,
    normal_wave: np.ndarray,
    pac_metadata: dict,
    normal_metadata: dict,
    pac_rr: float | None,
    normal_rr: float | None,
    output_dir: Path,
) -> Path:
    """PAC 파형과 같은 record의 정상 파형을 나란히 비교해 저장합니다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pac_signal = pac_wave.squeeze()
    normal_signal = normal_wave.squeeze()
    fs = pac_metadata["fs"]
    time_axis = np.arange(len(pac_signal)) / fs - 0.2
    rr_text = format_rr_difference(pac_rr, normal_rr)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

    axes[0].plot(time_axis, pac_signal, color="crimson", linewidth=1.3)
    axes[0].axvline(0, color="black", linestyle="--", linewidth=1, label="R-peak")
    axes[0].set_title("판독 대상: PAC(A) 예측 파형")
    axes[0].set_xlabel("R-peak 기준 시간(초)")
    axes[0].set_ylabel("정규화 전압(0~1)")
    axes[0].grid(True, alpha=0.25)
    axes[0].text(
        0.02,
        0.95,
        f"Record {pac_metadata['record']}\nRR={pac_rr:.3f}초" if pac_rr else "RR 계산 불가",
        transform=axes[0].transAxes,
        va="top",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
    )

    axes[1].plot(time_axis, normal_signal, color="steelblue", linewidth=1.3)
    axes[1].axvline(0, color="black", linestyle="--", linewidth=1, label="R-peak")
    axes[1].set_title("비교 대상: 같은 record의 정상(N) 파형")
    axes[1].set_xlabel("R-peak 기준 시간(초)")
    axes[1].grid(True, alpha=0.25)
    axes[1].text(
        0.02,
        0.95,
        f"Record {normal_metadata['record']}\nRR={normal_rr:.3f}초" if normal_rr else "RR 계산 불가",
        transform=axes[1].transAxes,
        va="top",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.85},
    )

    fig.suptitle(f"PAC와 정상 박동 비교: {rr_text}", fontsize=15, fontweight="bold")
    fig.tight_layout()
    output_path = output_dir / "pac_vs_normal_comparison.png"
    fig.savefig(output_path, dpi=170)
    if "agg" not in plt.get_backend().lower():
        plt.show()
    plt.close(fig)
    return output_path


def find_last_conv1d_layer(model: keras.Model):
    """Grad-CAM에 사용할 마지막 Conv1D layer를 찾습니다."""
    for layer in reversed(model.layers):
        if isinstance(layer, keras.layers.Conv1D):
            return layer
    return None


def make_1d_gradcam(model: keras.Model, sample: np.ndarray, class_index: int) -> np.ndarray | None:
    """1D-CNN이 어느 시간 구간을 중요하게 봤는지 Grad-CAM 값으로 계산합니다."""
    conv_layer = find_last_conv1d_layer(model)
    if conv_layer is None:
        return None

    grad_model = keras.Model(
        inputs=model.inputs,
        outputs=[conv_layer.output, model.output],
    )

    sample_batch = np.expand_dims(sample, axis=0)
    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(sample_batch)
        target_score = predictions[:, class_index]

    gradients = tape.gradient(target_score, conv_outputs)
    if gradients is None:
        return None

    weights = tf.reduce_mean(gradients, axis=1)
    cam = tf.reduce_sum(conv_outputs[0] * weights[0], axis=-1).numpy()
    cam = np.maximum(cam, 0)

    if np.max(cam) > 0:
        cam = cam / np.max(cam)

    # Conv layer 출력 길이를 원래 ECG 길이에 맞춰 보간합니다.
    original_length = sample.shape[0]
    conv_time = np.linspace(0, original_length - 1, num=len(cam))
    original_time = np.arange(original_length)
    return np.interp(original_time, conv_time, cam)


def plot_gradcam(
    pac_wave: np.ndarray,
    gradcam: np.ndarray | None,
    pac_metadata: dict,
    output_dir: Path,
) -> Path | None:
    """PAC 파형 위에 Grad-CAM heatmap을 겹쳐 저장합니다."""
    if gradcam is None:
        print("Grad-CAM을 계산하지 못했습니다. Conv1D layer 또는 gradient를 확인해 주세요.")
        return None

    signal = pac_wave.squeeze()
    fs = pac_metadata["fs"]
    time_axis = np.arange(len(signal)) / fs - 0.2

    fig, ax = plt.subplots(figsize=(13, 5))
    scatter = ax.scatter(
        time_axis,
        signal,
        c=gradcam,
        cmap="Reds",
        s=22,
        label="Grad-CAM 중요도",
    )
    ax.plot(time_axis, signal, color="black", linewidth=0.8, alpha=0.55)
    ax.axvline(0, color="black", linestyle="--", linewidth=1, label="R-peak")
    ax.set_title("PAC 예측에 영향을 준 파형 구간(1D Grad-CAM)")
    ax.set_xlabel("R-peak 기준 시간(초)")
    ax.set_ylabel("정규화 전압(0~1)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right")
    fig.colorbar(scatter, ax=ax, label="모델이 중요하게 본 정도")
    fig.tight_layout()

    output_path = output_dir / "pac_gradcam_heatmap.png"
    fig.savefig(output_path, dpi=170)
    if "agg" not in plt.get_backend().lower():
        plt.show()
    plt.close(fig)
    return output_path


def main() -> None:
    """PAC로 예측된 샘플을 골라 비교 시각화와 설명 문장을 만듭니다."""
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model_path = find_model_path(MODEL_DIR)
    print(f"모델 로드: {model_path}")
    model = keras.models.load_model(model_path)

    _, label_to_name = load_label_info(DATA_DIR)
    X_test, y_test, X_all, y_all = load_dataset(DATA_DIR)
    metadata_test = load_metadata(DATA_DIR / "metadata_test.csv")
    metadata_all = load_metadata(DATA_DIR / "metadata_all.csv")

    selected_test_index, pac_probability, pac_metadata = choose_predicted_pac_sample(
        model, X_test, metadata_test
    )
    normal_all_index = find_same_record_normal_index(pac_metadata, metadata_all)
    normal_metadata = metadata_all[normal_all_index]

    pac_wave = X_test[selected_test_index]
    normal_wave = X_all[normal_all_index]

    pac_rr = calculate_previous_rr(pac_metadata, metadata_all)
    normal_rr = calculate_previous_rr(normal_metadata, metadata_all)

    comparison_path = plot_comparison_view(
        pac_wave,
        normal_wave,
        pac_metadata,
        normal_metadata,
        pac_rr,
        normal_rr,
        OUTPUT_DIR,
    )

    gradcam = make_1d_gradcam(model, pac_wave, PAC_LABEL)
    gradcam_path = plot_gradcam(pac_wave, gradcam, pac_metadata, OUTPUT_DIR)

    summary = summarize_pac_reason(
        pac_metadata,
        normal_metadata,
        pac_probability,
        label_to_name,
        pac_rr,
        normal_rr,
    )
    summary_path = OUTPUT_DIR / "pac_explanation_summary.txt"
    with summary_path.open("w", encoding="utf-8") as text_file:
        text_file.write(summary)

    print("\n" + summary)
    print("=== 저장된 설명 자료 ===")
    print(f"비교 시각화: {comparison_path}")
    if gradcam_path:
        print(f"Grad-CAM heatmap: {gradcam_path}")
    print(f"임상 근거 요약: {summary_path}")
    print(
        "\nStreamlit 앱에서는 위 이미지와 summary 텍스트를 판독 결과 페이지에 그대로 배치하면 됩니다."
    )


if __name__ == "__main__":
    main()
