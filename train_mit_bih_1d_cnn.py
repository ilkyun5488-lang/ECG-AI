"""전처리된 MIT-BIH 심박 데이터를 이용해 1D-CNN 분류 모델을 학습합니다."""

from collections import Counter
from pathlib import Path
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
    from tensorflow.keras import layers
except ImportError as exc:
    raise SystemExit(
        "TensorFlow가 설치되어 있지 않습니다.\n"
        "터미널에서 아래 명령어를 먼저 실행해 주세요.\n\n"
        "pip install tensorflow scikit-learn matplotlib numpy"
    ) from exc

try:
    from sklearn.metrics import classification_report, confusion_matrix
except ImportError as exc:
    raise SystemExit(
        "scikit-learn이 설치되어 있지 않습니다.\n"
        "터미널에서 아래 명령어를 먼저 실행해 주세요.\n\n"
        "pip install scikit-learn"
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
OUTPUT_DIR = DATA_DIR / "cnn_model"

RANDOM_SEED = 42
EPOCHS = 30
BATCH_SIZE = 256
VALIDATION_SPLIT = 0.15


def set_random_seed(seed: int = RANDOM_SEED) -> None:
    """재현 가능한 학습을 위해 난수 시드를 고정합니다."""
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)


def load_label_info(data_dir: Path) -> tuple[dict[int, str], list[str]]:
    """label_map.json을 읽어 숫자 라벨과 이름을 연결합니다."""
    label_map_path = data_dir / "label_map.json"
    if not label_map_path.exists():
        raise FileNotFoundError(f"label_map.json을 찾을 수 없습니다: {label_map_path}")

    with label_map_path.open("r", encoding="utf-8") as json_file:
        label_info = json.load(json_file)

    symbol_to_label = {symbol: int(label) for symbol, label in label_info["label_map"].items()}
    descriptions = label_info["label_description"]
    label_to_name = {
        label: f"{symbol} ({descriptions[symbol]})"
        for symbol, label in symbol_to_label.items()
    }
    target_names = [label_to_name[idx] for idx in sorted(label_to_name)]
    return label_to_name, target_names


def load_dataset(data_dir: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """저장된 npy 파일을 불러옵니다."""
    required_files = ["X_train.npy", "y_train.npy", "X_test.npy", "y_test.npy"]
    missing_files = [name for name in required_files if not (data_dir / name).exists()]
    if missing_files:
        raise FileNotFoundError(f"다음 파일이 없습니다: {', '.join(missing_files)}")

    X_train = np.load(data_dir / "X_train.npy").astype(np.float32)
    y_train = np.load(data_dir / "y_train.npy").astype(np.int64)
    X_test = np.load(data_dir / "X_test.npy").astype(np.float32)
    y_test = np.load(data_dir / "y_test.npy").astype(np.int64)

    print("\n=== 데이터 로드 결과 ===")
    print(f"X_train shape: {X_train.shape}")
    print(f"y_train shape: {y_train.shape}")
    print(f"X_test shape: {X_test.shape}")
    print(f"y_test shape: {y_test.shape}")
    print("해석: X는 한 심박 파형이고, y는 N/PAC/PVC를 숫자로 바꾼 라벨입니다.")
    return X_train, y_train, X_test, y_test


def compute_class_weight(y_train: np.ndarray) -> dict[int, float]:
    """정상 박동이 너무 많은 문제를 줄이기 위해 class_weight를 계산합니다."""
    label_counts = Counter(y_train.tolist())
    total_count = len(y_train)
    class_count = len(label_counts)

    class_weight = {
        label: total_count / (class_count * count)
        for label, count in sorted(label_counts.items())
    }

    print("\n=== 클래스 불균형 보정값(class_weight) ===")
    for label, weight in class_weight.items():
        print(f"라벨 {label}: {weight:.3f}  (학습 샘플 {label_counts[label]:,}개)")
    print("해석: 샘플 수가 적은 PAC/PVC에 더 큰 가중치를 주어 모델이 무시하지 않도록 합니다.")
    return class_weight


def build_1d_cnn(input_shape: tuple[int, int], num_classes: int) -> keras.Model:
    """ECG beat 분류를 위한 1D-CNN 모델을 만듭니다."""
    model = keras.Sequential(
        [
            layers.Input(shape=input_shape),
            layers.Conv1D(32, kernel_size=7, padding="same", activation="relu"),
            layers.BatchNormalization(),
            layers.MaxPool1D(pool_size=2),
            layers.Dropout(0.20),

            layers.Conv1D(64, kernel_size=5, padding="same", activation="relu"),
            layers.BatchNormalization(),
            layers.MaxPool1D(pool_size=2),
            layers.Dropout(0.25),

            layers.Conv1D(128, kernel_size=3, padding="same", activation="relu"),
            layers.BatchNormalization(),
            layers.MaxPool1D(pool_size=2),
            layers.Dropout(0.30),

            layers.Conv1D(128, kernel_size=3, padding="same", activation="relu"),
            layers.BatchNormalization(),
            layers.GlobalAveragePooling1D(),

            layers.Dense(96, activation="relu"),
            layers.Dropout(0.40),
            layers.Dense(num_classes, activation="softmax"),
        ]
    )

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def plot_training_history(history: keras.callbacks.History, output_dir: Path) -> Path:
    """학습 과정의 loss와 accuracy 그래프를 저장합니다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    history_dict = history.history
    epochs = range(1, len(history_dict["loss"]) + 1)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    axes[0].plot(epochs, history_dict["loss"], label="Train Loss")
    axes[0].plot(epochs, history_dict["val_loss"], label="Validation Loss")
    axes[0].set_title("Loss 변화")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend()

    axes[1].plot(epochs, history_dict["accuracy"], label="Train Accuracy")
    axes[1].plot(epochs, history_dict["val_accuracy"], label="Validation Accuracy")
    axes[1].set_title("Accuracy 변화")
    axes[1].set_xlabel("Epoch")
    axes[1].set_ylabel("Accuracy")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend()

    fig.tight_layout()
    output_path = output_dir / "training_history.png"
    fig.savefig(output_path, dpi=160)
    if "agg" not in plt.get_backend().lower():
        plt.show()
    plt.close(fig)
    return output_path


def plot_confusion_matrix(cm: np.ndarray, target_names: list[str], output_dir: Path) -> Path:
    """혼동 행렬을 이미지로 저장합니다."""
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(cm, cmap="Blues")
    fig.colorbar(im, ax=ax)

    ax.set_title("Confusion Matrix")
    ax.set_xlabel("예측 라벨")
    ax.set_ylabel("실제 라벨")
    ax.set_xticks(np.arange(len(target_names)))
    ax.set_yticks(np.arange(len(target_names)))
    ax.set_xticklabels(target_names, rotation=30, ha="right")
    ax.set_yticklabels(target_names)

    max_value = cm.max() if cm.size else 0
    threshold = max_value / 2 if max_value else 0
    for row in range(cm.shape[0]):
        for col in range(cm.shape[1]):
            color = "white" if cm[row, col] > threshold else "black"
            ax.text(col, row, f"{cm[row, col]:,}", ha="center", va="center", color=color)

    fig.tight_layout()
    output_path = output_dir / "confusion_matrix.png"
    fig.savefig(output_path, dpi=160)
    if "agg" not in plt.get_backend().lower():
        plt.show()
    plt.close(fig)
    return output_path


def evaluate_model(
    model: keras.Model,
    X_test: np.ndarray,
    y_test: np.ndarray,
    target_names: list[str],
    output_dir: Path,
) -> None:
    """테스트 데이터로 모델 성능을 평가하고 결과를 저장합니다."""
    test_loss, test_accuracy = model.evaluate(X_test, y_test, verbose=0)
    probabilities = model.predict(X_test, batch_size=BATCH_SIZE, verbose=0)
    y_pred = np.argmax(probabilities, axis=1)

    cm = confusion_matrix(y_test, y_pred)
    report = classification_report(
        y_test,
        y_pred,
        target_names=target_names,
        digits=4,
        zero_division=0,
    )

    print("\n=== Test 성능 ===")
    print(f"Test Loss: {test_loss:.4f}")
    print(f"Test Accuracy: {test_accuracy:.4f}")
    print("\n=== Confusion Matrix ===")
    print(cm)
    print("\n=== Classification Report ===")
    print(report)

    pac_label = 1
    pac_total = int(np.sum(y_test == pac_label))
    pac_correct = int(np.sum((y_test == pac_label) & (y_pred == pac_label)))
    pac_recall = pac_correct / pac_total if pac_total else 0
    print(
        f"\nPAC(A) 확인: 실제 PAC {pac_total:,}개 중 {pac_correct:,}개를 PAC로 맞췄습니다. "
        f"PAC recall={pac_recall:.4f}"
    )

    report_path = output_dir / "classification_report.txt"
    with report_path.open("w", encoding="utf-8") as text_file:
        text_file.write("=== Test 성능 ===\n")
        text_file.write(f"Test Loss: {test_loss:.4f}\n")
        text_file.write(f"Test Accuracy: {test_accuracy:.4f}\n\n")
        text_file.write("=== Confusion Matrix ===\n")
        text_file.write(str(cm))
        text_file.write("\n\n=== Classification Report ===\n")
        text_file.write(report)
        text_file.write(
            f"\nPAC(A) 확인: 실제 PAC {pac_total:,}개 중 {pac_correct:,}개를 PAC로 맞춤. "
            f"PAC recall={pac_recall:.4f}\n"
        )

    cm_path = plot_confusion_matrix(cm, target_names, output_dir)
    print(f"\nClassification report 저장: {report_path}")
    print(f"Confusion matrix 이미지 저장: {cm_path}")


def main() -> None:
    """1D-CNN 모델을 학습하고 평가합니다."""
    set_random_seed()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    X_train, y_train, X_test, y_test = load_dataset(DATA_DIR)
    label_to_name, target_names = load_label_info(DATA_DIR)
    num_classes = len(label_to_name)
    class_weight = compute_class_weight(y_train)

    model = build_1d_cnn(input_shape=X_train.shape[1:], num_classes=num_classes)
    print("\n=== 1D-CNN 모델 구조 ===")
    model.summary()

    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=6,
            restore_best_weights=True,
            verbose=1,
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=3,
            min_lr=1e-6,
            verbose=1,
        ),
        keras.callbacks.ModelCheckpoint(
            filepath=OUTPUT_DIR / "best_mit_bih_1d_cnn.keras",
            monitor="val_loss",
            save_best_only=True,
            verbose=1,
        ),
    ]

    history = model.fit(
        X_train,
        y_train,
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        validation_split=VALIDATION_SPLIT,
        class_weight=class_weight,
        callbacks=callbacks,
        verbose=1,
    )

    history_path = plot_training_history(history, OUTPUT_DIR)
    final_model_path = OUTPUT_DIR / "mit_bih_1d_cnn_final.keras"
    model.save(final_model_path)

    print(f"\n학습 곡선 저장: {history_path}")
    print(f"최종 모델 저장: {final_model_path}")
    print(f"가장 좋은 모델 저장: {OUTPUT_DIR / 'best_mit_bih_1d_cnn.keras'}")

    evaluate_model(model, X_test, y_test, target_names, OUTPUT_DIR)

    print(
        "\n다음 단계 제안: PAC로 예측된 샘플의 R-peak 주변 파형, P파 위치, RR 간격 특징을 함께 시각화하면 "
        "'이 파형은 왜 PAC인가?'를 설명하는 화면으로 확장할 수 있습니다."
    )


if __name__ == "__main__":
    main()
