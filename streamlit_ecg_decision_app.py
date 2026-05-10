"""AI와 사용자가 함께 부정맥을 찾아가는 Streamlit 프로토타입 앱."""

from __future__ import annotations

from pathlib import Path
import csv
import io
import json
import os
import platform
import random

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from PIL import Image

os.environ.setdefault("KERAS_BACKEND", "tensorflow")

try:
    import cv2
except ImportError:
    cv2 = None

try:
    import tensorflow as tf
    from tensorflow import keras
except ImportError:
    tf = None
    keras = None


# 운영체제에 따라 한글 폰트 자동 설정
if platform.system() == "Windows":
    plt.rcParams["font.family"] = "Malgun Gothic"
elif platform.system() == "Darwin":  # macOS
    plt.rcParams["font.family"] = "AppleGothic"
else:  # Linux
    plt.rcParams["font.family"] = "NanumGothic"

plt.rcParams["axes.unicode_minus"] = False  # 마이너스 기호 깨짐 방지


DATA_DIR = Path(
    r"c:\Users\ilkyu\OneDrive\Desktop\김일균\간호대학원\5학기\의료인공지능개론\커서 실습\data\mit_bih_preprocessed"
)
MODEL_DIR = DATA_DIR / "cnn_model"
RANDOM_SEED = 42
DEFAULT_FS = 360.0
PRE_R_SECONDS = 0.2


QUESTION_BANK = {
    "A": {
        "title": "PAC(심방조기수축) 감별 질문",
        "questions": [
            "정상 박동보다 일찍 나타난 조기 박동으로 보이나요?",
            "QRS 앞에 P파가 보이거나, P파 모양이 평소와 달라 보이나요?",
            "QRS 폭은 대체로 좁게 보이나요?",
        ],
        "rationale": "PAC는 심방에서 일찍 시작된 박동이므로 RR 간격이 짧아지고, 조기 P파가 보이거나 T파에 숨어 보일 수 있습니다.",
    },
    "V": {
        "title": "PVC(심실조기수축) 감별 질문",
        "questions": [
            "QRS 폭이 0.12초 이상으로 넓어 보이나요?",
            "조기 박동 앞에 명확한 P파가 잘 보이지 않나요?",
            "PVC 뒤에 보상성 휴지기(compensatory pause)가 있어 보이나요?",
        ],
        "rationale": "PVC는 심실에서 일찍 시작된 박동이므로 QRS가 넓고 모양이 다르며, 앞선 P파가 뚜렷하지 않은 경우가 많습니다.",
    },
    "L": {
        "title": "LBBB(좌각차단) 감별 질문",
        "questions": [
            "QRS 폭이 0.12초 이상으로 넓어 보이나요?",
            "V1에서 깊고 넓은 S파 또는 QS 형태가 보이나요?",
            "I, V5, V6에서 넓고 둔한 R파가 보이나요?",
        ],
        "rationale": "LBBB는 좌심실 전도가 늦어져 QRS가 넓어지고, 좌측 흉부유도에서 넓은 R파가 특징적으로 보일 수 있습니다.",
    },
    "R": {
        "title": "RBBB(우각차단) 감별 질문",
        "questions": [
            "QRS 폭이 0.12초 이상으로 넓어 보이나요?",
            "V1-V2에서 rSR' 또는 토끼 귀 모양이 보이나요?",
            "I, V5, V6에서 넓은 S파가 보이나요?",
        ],
        "rationale": "RBBB는 우심실 전도가 늦어져 V1-V2의 rSR' 형태와 좌측 lead의 넓은 S파가 단서가 됩니다.",
    },
    "N": {
        "title": "정상 박동 감별 질문",
        "questions": [
            "박동이 예상되는 위치에 규칙적으로 나타나나요?",
            "QRS 앞에 일정한 P파가 보이나요?",
            "QRS 폭이 좁고 모양이 안정적으로 보이나요?",
        ],
        "rationale": "정상 박동은 P-QRS-T 순서가 유지되고, QRS가 좁고, 주변 박동과 비교해 지나치게 빠르거나 늦지 않습니다.",
    },
}


def apply_index_style_theme() -> None:
    """index.html의 어두운 앱 스타일을 Streamlit 화면에 맞게 적용합니다."""
    st.markdown(
        """
        <style>
        :root {
          --bg: #0b1220;
          --panel: rgba(255, 255, 255, 0.06);
          --panel-2: rgba(255, 255, 255, 0.08);
          --text: rgba(255, 255, 255, 0.92);
          --muted: rgba(255, 255, 255, 0.68);
          --border: rgba(255, 255, 255, 0.14);
          --accent: #46c2ff;
          --accent-2: #7c5cff;
          --danger: #ff5a6a;
          --radius: 18px;
        }

        .stApp {
          background:
            radial-gradient(1200px 800px at 10% -10%, rgba(70, 194, 255, 0.22), transparent 60%),
            radial-gradient(900px 700px at 110% 0%, rgba(124, 92, 255, 0.18), transparent 55%),
            var(--bg);
          color: var(--text);
        }

        [data-testid="stHeader"] {
          background: rgba(11, 18, 32, 0.78);
          backdrop-filter: blur(10px);
        }

        [data-testid="stSidebar"] {
          background: rgba(11, 18, 32, 0.92);
          border-right: 1px solid rgba(255, 255, 255, 0.08);
        }

        .block-container {
          max-width: 1060px;
          padding-top: 1.2rem;
          padding-bottom: 2rem;
        }

        .ecg-topbar {
          position: sticky;
          top: 0;
          z-index: 20;
          margin: -1.2rem -0.5rem 1rem -0.5rem;
          padding: 22px 18px 14px;
          background: linear-gradient(to bottom, rgba(11, 18, 32, 0.96), rgba(11, 18, 32, 0.62));
          backdrop-filter: blur(10px);
          border-bottom: 1px solid rgba(255, 255, 255, 0.06);
        }

        .ecg-topbar__title {
          font-size: 20px;
          font-weight: 850;
          letter-spacing: -0.2px;
        }

        .ecg-topbar__subtitle {
          margin-top: 4px;
          color: var(--muted);
          font-size: 13px;
        }

        .ecg-hero, .ecg-card, div[data-testid="stMetric"], div[data-testid="stExpander"] {
          border: 1px solid var(--border);
          border-radius: var(--radius);
          background: linear-gradient(180deg, var(--panel-2), var(--panel));
          box-shadow: 0 12px 32px rgba(0, 0, 0, 0.28);
        }

        .ecg-hero {
          padding: 16px;
          margin-bottom: 14px;
        }

        .ecg-kicker {
          color: var(--muted);
          font-size: 12px;
          margin-bottom: 8px;
        }

        .ecg-title {
          font-size: 22px;
          font-weight: 900;
          margin: 0;
        }

        .ecg-desc {
          margin-top: 10px;
          color: var(--muted);
          font-size: 13px;
          line-height: 1.55;
        }

        .ecg-badge {
          display: inline-block;
          margin-left: 8px;
          padding: 4px 8px;
          border-radius: 999px;
          border: 1px solid rgba(70, 194, 255, 0.32);
          background: rgba(70, 194, 255, 0.12);
          color: rgba(220, 248, 255, 0.95);
          font-size: 11px;
          font-weight: 800;
        }

        .ecg-footer {
          margin-top: 24px;
          padding: 12px 4px 0;
          border-top: 1px solid rgba(255, 255, 255, 0.08);
          color: var(--muted);
          font-size: 12px;
          line-height: 1.45;
        }

        .stButton > button, .stDownloadButton > button {
          border-radius: 12px;
          border: 1px solid rgba(70, 194, 255, 0.32);
          background: rgba(70, 194, 255, 0.12);
          color: rgba(220, 248, 255, 0.95);
          font-weight: 850;
        }

        .stAlert {
          border-radius: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    """앱 상단 바와 소개 영역을 그립니다."""
    st.markdown(
        """
        <div class="ecg-topbar">
          <div class="ecg-topbar__title">심전도 판독 AI</div>
          <div class="ecg-topbar__subtitle">간호사 교육용 · 참고용 · AI + 사용자 감별 질문</div>
        </div>

        <section class="ecg-hero">
          <div class="ecg-kicker">AI 부정맥 판독 엔진</div>
          <h1 class="ecg-title">카메라로 찍고, AI와 함께 부정맥을 찾아갑니다</h1>
          <div class="ecg-desc">
            촬영 이미지 또는 전처리된 파형을 입력하면 AI가 후보를 제시하고,
            사용자가 핵심 감별 질문에 답하면서 최종 결과를 정리합니다.
            <span class="ecg-badge">교육용</span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_footer() -> None:
    """index.html과 같은 교육용 고지 문구를 하단에 표시합니다."""
    st.markdown(
        """
        <div class="ecg-footer">
          본 앱은 교육용이며 참고용으로만 사용하시기 바랍니다.
          의학적인 자문이나 진단이 필요한 경우 전문가에게 문의하세요.
          카메라 이미지 digitization 결과는 촬영 각도, 격자 왜곡, 조명, 해상도에 따라 달라질 수 있습니다.
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_query_mode() -> str | None:
    """URL query parameter로 전달된 시작 모드를 읽습니다."""
    mode = st.query_params.get("mode", None)
    if isinstance(mode, list):
        mode = mode[0] if mode else None
    if mode == "camera":
        return "카메라로 찾기"
    if mode == "upload":
        return "파일 업로드"
    if mode == "sample":
        return "심전도 학습 데이터"
    return None


def initialize_input_mode() -> None:
    """화면 전환에 사용할 Streamlit session state를 초기화합니다."""
    query_mode = get_query_mode()
    if query_mode is not None:
        st.session_state.input_mode = query_mode
    if "input_mode" not in st.session_state:
        st.session_state.input_mode = "심전도 학습 데이터"


def render_mode_buttons() -> None:
    """메인 화면에서 판독 모드로 매끄럽게 넘어가는 버튼을 표시합니다."""
    col_sample, col_upload, col_camera = st.columns(3)
    with col_sample:
        if st.button("학습 데이터로 테스트", use_container_width=True):
            st.session_state.input_mode = "심전도 학습 데이터"
            st.rerun()
    with col_upload:
        if st.button("파형 파일 업로드", use_container_width=True):
            st.session_state.input_mode = "파일 업로드"
            st.rerun()
    with col_camera:
        if st.button("카메라로 찾기", use_container_width=True, type="primary"):
            st.session_state.input_mode = "카메라로 찾기"
            st.rerun()


@st.cache_resource
def load_model(model_path_text: str):
    """Keras 모델을 한 번만 로드합니다."""
    if keras is None:
        return None
    return keras.models.load_model(model_path_text)


@st.cache_data
def load_label_info(data_dir_text: str) -> tuple[dict[str, int], dict[int, str], dict[int, str]]:
    """label_map.json을 읽어 symbol, label, 설명을 연결합니다."""
    data_dir = Path(data_dir_text)
    with (data_dir / "label_map.json").open("r", encoding="utf-8") as json_file:
        label_info = json.load(json_file)

    symbol_to_label = {symbol: int(label) for symbol, label in label_info["label_map"].items()}
    descriptions = label_info["label_description"]
    label_to_symbol = {label: symbol for symbol, label in symbol_to_label.items()}
    label_to_name = {
        label: f"{symbol} ({descriptions.get(symbol, symbol)})"
        for symbol, label in symbol_to_label.items()
    }
    return symbol_to_label, label_to_symbol, label_to_name


@st.cache_data
def load_builtin_dataset(data_dir_text: str):
    """전처리된 테스트 데이터와 메타데이터를 불러옵니다."""
    data_dir = Path(data_dir_text)
    X_test = np.load(data_dir / "X_test.npy").astype(np.float32)
    y_test = np.load(data_dir / "y_test.npy").astype(np.int64)
    X_all = np.load(data_dir / "X_all.npy").astype(np.float32)
    metadata_test = load_metadata(data_dir / "metadata_test.csv")
    metadata_all = load_metadata(data_dir / "metadata_all.csv")
    return X_test, y_test, X_all, metadata_test, metadata_all


def load_metadata(path: Path) -> list[dict]:
    """CSV 메타데이터를 읽어 숫자 필드는 숫자로 변환합니다."""
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


def find_model_path(model_dir: Path) -> Path | None:
    """저장된 Keras 모델 경로를 찾습니다."""
    candidates = [
        model_dir / "best_mit_bih_1d_cnn.keras",
        model_dir / "mit_bih_1d_cnn_final.keras",
        model_dir / "best_mit_bih_1d_cnn.h5",
        model_dir / "mit_bih_1d_cnn_final.h5",
    ]
    for path in candidates:
        if path.exists():
            return path

    keras_files = sorted(model_dir.glob("*.keras")) + sorted(model_dir.glob("*.h5"))
    return keras_files[0] if keras_files else None


def normalize_uploaded_waveform(waveform: np.ndarray, target_length: int) -> np.ndarray:
    """업로드된 단일 파형을 모델 입력 shape에 맞게 정리합니다."""
    waveform = np.asarray(waveform, dtype=np.float32).squeeze()
    if waveform.ndim != 1:
        raise ValueError("업로드 파형은 1차원 배열이어야 합니다.")

    if len(waveform) != target_length:
        old_axis = np.linspace(0, 1, num=len(waveform))
        new_axis = np.linspace(0, 1, num=target_length)
        waveform = np.interp(new_axis, old_axis, waveform).astype(np.float32)

    min_value = float(np.min(waveform))
    max_value = float(np.max(waveform))
    if np.isclose(min_value, max_value):
        waveform = np.zeros_like(waveform, dtype=np.float32)
    else:
        waveform = ((waveform - min_value) / (max_value - min_value)).astype(np.float32)

    return waveform[:, np.newaxis]


def read_uploaded_waveform(uploaded_file, target_length: int) -> np.ndarray:
    """npy 또는 csv/txt 파일에서 단일 ECG 파형을 읽습니다."""
    suffix = Path(uploaded_file.name).suffix.lower()
    raw_bytes = uploaded_file.getvalue()

    if suffix == ".npy":
        waveform = np.load(io.BytesIO(raw_bytes), allow_pickle=False)
    elif suffix in {".csv", ".txt"}:
        text = raw_bytes.decode("utf-8-sig")
        waveform = np.loadtxt(io.StringIO(text), delimiter="," if suffix == ".csv" else None)
    else:
        raise ValueError("지원 형식은 .npy, .csv, .txt 입니다.")

    return normalize_uploaded_waveform(waveform, target_length)


def digitize_ecg_image(image_bytes: bytes, target_length: int) -> tuple[np.ndarray, dict]:
    """카메라/업로드 ECG 이미지에서 검은 파형선을 추출해 모델 입력 파형으로 변환합니다.

    이 함수는 최종 의료기기 수준의 digitization이 아니라, 앱 프로토타입을 위한
    기초 파이프라인입니다. 실제 서비스에서는 격자 보정, lead 영역 검출, 스케일 보정,
    R-peak 검출을 더 정교하게 만들어야 합니다.
    """
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    rgb = np.array(image)
    gray = np.array(image.convert("L"))

    if cv2 is not None:
        # ECG trace는 보통 어둡고, 배경 격자는 붉은색입니다.
        # 빨간 격자를 최대한 제외하고 검은 trace/문자만 남기는 단순 마스크입니다.
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        saturation = hsv[:, :, 1]
        value = hsv[:, :, 2]
        dark_mask = (value < 105) & (saturation < 120)

        mask = dark_mask.astype(np.uint8) * 255
        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    else:
        # OpenCV가 없는 환경에서도 동작하는 최소 fallback입니다.
        mask = (gray < 95).astype(np.uint8) * 255

    height, width = mask.shape
    x_points: list[int] = []
    y_points: list[float] = []

    # 각 x좌표마다 검은 픽셀들의 중앙 y값을 ECG 선 위치로 봅니다.
    for x in range(width):
        ys = np.where(mask[:, x] > 0)[0]
        if len(ys) < 2:
            continue

        # lead 라벨 같은 글자 영역 영향을 줄이기 위해 중앙값을 사용합니다.
        x_points.append(x)
        y_points.append(float(np.median(ys)))

    if len(x_points) < max(20, width * 0.05):
        raise ValueError(
            "이미지에서 ECG 선을 충분히 추출하지 못했습니다. 더 가까이, 수평으로, 밝게 촬영해 주세요."
        )

    x_points_array = np.asarray(x_points, dtype=np.float32)
    y_points_array = np.asarray(y_points, dtype=np.float32)
    full_x = np.arange(width, dtype=np.float32)
    centerline_y = np.interp(full_x, x_points_array, y_points_array)

    # 이미지 좌표는 아래쪽이 큰 값이므로, 위로 올라가는 R파가 큰 값이 되도록 뒤집습니다.
    raw_signal = height - centerline_y
    raw_signal = moving_average(raw_signal, window_size=7)

    old_axis = np.linspace(0, 1, num=len(raw_signal))
    new_axis = np.linspace(0, 1, num=target_length)
    resampled_signal = np.interp(new_axis, old_axis, raw_signal).astype(np.float32)
    normalized_wave = normalize_uploaded_waveform(resampled_signal, target_length=target_length)

    debug_info = {
        "rgb": rgb,
        "mask": mask,
        "raw_signal": raw_signal,
        "resampled_signal": normalized_wave.squeeze(),
        "extracted_points": len(x_points),
        "image_width": width,
        "image_height": height,
    }
    return normalized_wave, debug_info


def moving_average(values: np.ndarray, window_size: int = 7) -> np.ndarray:
    """파형 추출 후 작은 떨림을 줄이기 위해 이동평균을 적용합니다."""
    if window_size <= 1:
        return values
    kernel = np.ones(window_size) / window_size
    return np.convolve(values, kernel, mode="same")


def estimate_r_peak_and_rr(wave: np.ndarray, fs: float = DEFAULT_FS) -> tuple[int, float | None]:
    """단일 파형에서 가장 높은 지점을 R-peak 후보로 잡고 단순 RR을 추정합니다."""
    signal = wave.squeeze()
    r_peak_index = int(np.argmax(signal))

    # 단일 beat 입력에서는 실제 이전 RR을 알 수 없습니다.
    # 대신 파형 안에서 큰 peak가 2개 이상 보이면 peak 간격을 매우 기초적으로 추정합니다.
    threshold = np.percentile(signal, 88)
    candidate_indices = np.where(signal >= threshold)[0]
    if len(candidate_indices) < 2:
        return r_peak_index, None

    groups: list[list[int]] = []
    current_group = [int(candidate_indices[0])]
    for idx in candidate_indices[1:]:
        idx = int(idx)
        if idx - current_group[-1] <= 3:
            current_group.append(idx)
        else:
            groups.append(current_group)
            current_group = [idx]
    groups.append(current_group)

    peak_indices = [int(np.mean(group)) for group in groups if len(group) >= 2]
    if len(peak_indices) < 2:
        return r_peak_index, None

    rr_seconds = abs(peak_indices[-1] - peak_indices[-2]) / fs
    return r_peak_index, rr_seconds


def plot_digitization_debug(debug_info: dict):
    """카메라 이미지가 수치 파형으로 바뀌는 과정을 확인하는 그림을 만듭니다."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    axes[0].imshow(debug_info["rgb"])
    axes[0].set_title("원본 이미지")
    axes[0].axis("off")

    axes[1].imshow(debug_info["mask"], cmap="gray")
    axes[1].set_title("추출된 검은 ECG 선")
    axes[1].axis("off")

    axes[2].plot(debug_info["resampled_signal"], color="crimson", linewidth=1.3)
    axes[2].set_title("모델 입력용 1D 파형")
    axes[2].set_xlabel("time step")
    axes[2].set_ylabel("0~1 정규화")
    axes[2].grid(True, alpha=0.25)

    fig.tight_layout()
    return fig


def get_top_candidates(probabilities: np.ndarray, label_to_symbol: dict[int, str], top_k: int = 3) -> list[dict]:
    """모델 확률에서 상위 후보를 추립니다."""
    top_indices = np.argsort(probabilities)[::-1][:top_k]
    return [
        {
            "label": int(label),
            "symbol": label_to_symbol.get(int(label), str(label)),
            "probability": float(probabilities[label]),
        }
        for label in top_indices
    ]


def calculate_previous_rr(metadata_row: dict | None, metadata_all: list[dict] | None) -> float | None:
    """해당 심박 직전 R-peak와의 RR 간격을 계산합니다."""
    if metadata_row is None or metadata_all is None:
        return None

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


def find_nearest_normal_sample(metadata_row: dict | None, metadata_all: list[dict], X_all: np.ndarray):
    """같은 record에서 가장 가까운 정상(N) 파형을 찾습니다."""
    if metadata_row is None:
        return None, None

    candidates = [
        (idx, row)
        for idx, row in enumerate(metadata_all)
        if row["record"] == metadata_row["record"] and row["symbol"] == "N"
    ]
    if not candidates:
        return None, None

    selected_index, selected_row = min(
        candidates,
        key=lambda item: abs(item[1]["r_peak_sample"] - metadata_row["r_peak_sample"]),
    )
    return X_all[selected_index], selected_row


def format_rr(rr: float | None) -> str:
    """RR 간격을 화면 표시용 문자열로 만듭니다."""
    return f"{rr:.3f}초" if rr is not None else "계산 불가"


def combine_ai_and_user_scores(candidates: list[dict], answers_by_symbol: dict[str, list[bool]]) -> list[dict]:
    """AI 확률과 사용자 Yes/No 답변을 결합해 최종 점수를 계산합니다."""
    scored_candidates = []

    for candidate in candidates:
        symbol = candidate["symbol"]
        answers = answers_by_symbol.get(symbol, [])
        yes_count = sum(answers)
        no_count = len(answers) - yes_count

        # 질문이 많이 맞을수록 후보 점수를 올리고, 아니오가 많으면 낮춥니다.
        evidence_multiplier = 1.0 + yes_count * 0.18 - no_count * 0.12
        evidence_multiplier = max(0.2, evidence_multiplier)
        final_score = candidate["probability"] * evidence_multiplier

        scored_candidates.append(
            {
                **candidate,
                "yes_count": yes_count,
                "no_count": no_count,
                "final_score": float(final_score),
            }
        )

    total_score = sum(item["final_score"] for item in scored_candidates)
    for item in scored_candidates:
        item["final_probability"] = item["final_score"] / total_score if total_score else 0

    return sorted(scored_candidates, key=lambda item: item["final_probability"], reverse=True)


def make_clinical_summary(best_result: dict, rr_text: str) -> str:
    """최종 후보에 대한 임상적 근거 요약을 만듭니다."""
    symbol = best_result["symbol"]
    rule = QUESTION_BANK.get(symbol, {})
    rationale = rule.get(
        "rationale",
        "AI 확률과 사용자 감별 질문 답변을 함께 고려해 가장 가능성이 높은 후보로 정리했습니다.",
    )
    return (
        f"최종 후보는 {symbol}입니다. "
        f"AI 확률과 사용자 확인 질문을 합친 최종 점수는 {best_result['final_probability']:.1%}입니다. "
        f"RR 간격은 {rr_text}입니다. {rationale} "
        "이 결과는 교육용 참고 자료이며 실제 진단은 원본 심전도와 환자 상태를 함께 보아야 합니다."
    )


def plot_waveform_report(
    target_wave: np.ndarray,
    target_metadata: dict | None,
    target_rr: float | None,
    normal_wave: np.ndarray | None,
    normal_metadata: dict | None,
    normal_rr: float | None,
    r_peak_index: int | None = None,
):
    """판독 파형과 정상 비교 파형을 한 리포트로 그립니다."""
    target_signal = target_wave.squeeze()
    fs = target_metadata["fs"] if target_metadata else 360.0
    time_axis = np.arange(len(target_signal)) / fs - 0.2
    if r_peak_index is None:
        r_peak_time = 0.0
    else:
        r_peak_time = r_peak_index / fs - PRE_R_SECONDS

    row_count = 2 if normal_wave is not None else 1
    fig, axes = plt.subplots(row_count, 1, figsize=(12, 6 if row_count == 2 else 4), sharex=True)
    if row_count == 1:
        axes = [axes]

    axes[0].plot(time_axis, target_signal, color="crimson", linewidth=1.25)
    axes[0].axvline(r_peak_time, color="black", linestyle="--", linewidth=1)
    axes[0].set_title("판독 대상 파형")
    axes[0].set_ylabel("정규화 전압")
    axes[0].grid(True, alpha=0.25)
    axes[0].text(
        0.01,
        0.92,
        f"R-peak = {r_peak_time:.3f}초\n이전 RR = {format_rr(target_rr)}",
        transform=axes[0].transAxes,
        va="top",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.88},
    )

    if normal_wave is not None:
        normal_signal = normal_wave.squeeze()
        axes[1].plot(time_axis, normal_signal, color="steelblue", linewidth=1.25)
        axes[1].axvline(0, color="black", linestyle="--", linewidth=1)
        axes[1].set_title("같은 record 내 정상(N) 비교 파형")
        axes[1].set_xlabel("R-peak 기준 시간(초)")
        axes[1].set_ylabel("정규화 전압")
        axes[1].grid(True, alpha=0.25)
        axes[1].text(
            0.01,
            0.92,
            f"Record {normal_metadata['record'] if normal_metadata else '-'}\n이전 RR = {format_rr(normal_rr)}",
            transform=axes[1].transAxes,
            va="top",
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.88},
        )
    else:
        axes[0].set_xlabel("R-peak 기준 시간(초)")

    fig.tight_layout()
    return fig


def render_candidate_questions(candidates: list[dict]) -> dict[str, list[bool]]:
    """상위 후보별 감별 질문을 체크박스로 표시합니다."""
    answers_by_symbol: dict[str, list[bool]] = {}

    for candidate in candidates:
        symbol = candidate["symbol"]
        rule = QUESTION_BANK.get(
            symbol,
            {
                "title": f"{symbol} 감별 질문",
                "questions": [
                    "AI가 제시한 후보와 일치하는 특징이 육안으로 보이나요?",
                    "주변 정상 박동과 비교했을 때 형태나 타이밍이 다르게 보이나요?",
                ],
            },
        )

        with st.expander(f"{rule['title']}  | AI 확률 {candidate['probability']:.1%}", expanded=True):
            answers = []
            for question_index, question in enumerate(rule["questions"]):
                answer = st.checkbox(
                    question,
                    key=f"question_{symbol}_{question_index}",
                )
                answers.append(answer)
            answers_by_symbol[symbol] = answers

    return answers_by_symbol


def show_probability_table(candidates: list[dict], label_to_name: dict[int, str]) -> None:
    """AI 후보 확률을 표 형태로 보여줍니다."""
    st.subheader("1단계. AI 후보")
    rows = []
    for candidate in candidates:
        rows.append(
            {
                "후보": label_to_name.get(candidate["label"], candidate["symbol"]),
                "AI 확률": f"{candidate['probability']:.1%}",
            }
        )
    st.table(rows)


def main() -> None:
    """Streamlit 앱 진입점입니다."""
    st.set_page_config(page_title="ECG AI 판독 프로토타입", layout="wide")
    apply_index_style_theme()
    render_header()
    initialize_input_mode()
    render_mode_buttons()

    if keras is None:
        st.error(
            "TensorFlow가 설치된 환경에서 실행해야 합니다. "
            "모델 학습에 사용한 가상환경을 활성화한 뒤 `streamlit run streamlit_ecg_decision_app.py`를 실행해 주세요."
        )
        st.stop()

    default_model_path = find_model_path(MODEL_DIR)
    st.sidebar.header("모델 설정")
    model_path_text = st.sidebar.text_input(
        "학습된 모델 파일 경로",
        value=str(default_model_path) if default_model_path else "",
        help="`.keras` 또는 `.h5` 모델 파일 경로를 입력합니다.",
    )
    model_path = Path(model_path_text) if model_path_text else None
    if model_path is None or not model_path.exists():
        st.error(
            "학습된 `.keras` 또는 `.h5` 모델을 찾지 못했습니다. "
            "모델 학습 후 저장된 파일 경로를 왼쪽 사이드바에 입력해 주세요."
        )
        st.stop()

    symbol_to_label, label_to_symbol, label_to_name = load_label_info(str(DATA_DIR))
    model = load_model(str(model_path))
    X_test, y_test, X_all, metadata_test, metadata_all = load_builtin_dataset(str(DATA_DIR))

    st.sidebar.header("입력 선택")
    input_mode = st.sidebar.radio(
        "분석할 파형 선택",
        ["심전도 학습 데이터", "파일 업로드", "카메라로 찾기"],
        key="input_mode",
    )
    st.sidebar.write(f"사용 모델: `{model_path.name}`")

    target_wave = None
    target_metadata = None
    normal_wave = None
    normal_metadata = None
    digitization_debug = None
    estimated_r_peak_index = None

    if input_mode == "심전도 학습 데이터":
        label_filter = st.sidebar.selectbox(
            "샘플 종류",
            ["전체"] + [label_to_name[label] for label in sorted(label_to_name)],
        )

        available_indices = list(range(len(X_test)))
        if label_filter != "전체":
            selected_label = next(label for label, name in label_to_name.items() if name == label_filter)
            available_indices = np.where(y_test == selected_label)[0].tolist()

        default_index = random.Random(RANDOM_SEED).choice(available_indices)
        selected_index = st.sidebar.selectbox(
            "테스트 샘플 index",
            available_indices,
            index=available_indices.index(default_index),
        )
        target_wave = X_test[selected_index]
        target_metadata = metadata_test[selected_index]
        normal_wave, normal_metadata = find_nearest_normal_sample(target_metadata, metadata_all, X_all)
    elif input_mode == "파일 업로드":
        uploaded_file = st.sidebar.file_uploader("단일 beat 파형 업로드", type=["npy", "csv", "txt"])
        st.sidebar.info("업로드 파형은 한 박동 길이의 1차원 배열이어야 합니다. 길이가 다르면 자동 보간합니다.")
        if uploaded_file is None:
            st.info("왼쪽에서 `.npy`, `.csv`, `.txt` 파형 파일을 업로드해 주세요.")
            st.stop()
        target_wave = read_uploaded_waveform(uploaded_file, target_length=X_test.shape[1])
        estimated_r_peak_index, estimated_rr = estimate_r_peak_and_rr(target_wave)
        target_metadata = None
    else:
        st.subheader("카메라로 찾기")
        st.write(
            "심전도 종이가 화면에 꽉 차도록 수평으로 촬영해 주세요. "
            "현재 digitization은 프로토타입이므로 한 박동 또는 짧은 rhythm strip을 가까이 촬영할수록 안정적입니다."
        )
        camera_image = st.camera_input("심전도 사진 촬영")
        uploaded_image = st.file_uploader("또는 심전도 이미지 업로드", type=["png", "jpg", "jpeg"])
        image_source = camera_image or uploaded_image

        if image_source is None:
            st.info("카메라 촬영 또는 이미지 업로드 후 AI 분석이 시작됩니다.")
            render_footer()
            st.stop()

        with st.spinner("AI가 분석 중입니다... 이미지에서 ECG 선을 추출하고 파형으로 변환하고 있습니다."):
            try:
                target_wave, digitization_debug = digitize_ecg_image(
                    image_source.getvalue(),
                    target_length=X_test.shape[1],
                )
                estimated_r_peak_index, estimated_rr = estimate_r_peak_and_rr(target_wave)
            except Exception as exc:
                st.error(f"이미지 digitization에 실패했습니다: {exc}")
                st.info("배경 격자가 선명하고 ECG trace가 진하게 보이도록 다시 촬영해 주세요.")
                render_footer()
                st.stop()

        st.success("이미지에서 1D ECG 파형을 추출했습니다.")
        with st.expander("이미지-수치 변환(Digitization) 과정 보기", expanded=True):
            st.pyplot(plot_digitization_debug(digitization_debug))
            st.caption(
                "파이프라인: RGB 이미지 → 검은 ECG trace 마스크 추출 → column별 중심선 연결 → "
                "1D 파형 보간 → 0~1 정규화 → 모델 입력 shape 변환"
            )

    with st.spinner("AI가 분석 중입니다... 부정맥 후보 확률을 계산하고 있습니다."):
        probabilities = model.predict(np.expand_dims(target_wave, axis=0), verbose=0)[0]
    candidates = get_top_candidates(probabilities, label_to_symbol, top_k=min(3, len(probabilities)))

    target_rr = calculate_previous_rr(target_metadata, metadata_all)
    if target_rr is None and "estimated_rr" in locals():
        target_rr = estimated_rr
    normal_rr = calculate_previous_rr(normal_metadata, metadata_all)

    col_left, col_right = st.columns([1.2, 1])
    with col_left:
        st.subheader("종합 시각화 리포트")
        fig = plot_waveform_report(
            target_wave,
            target_metadata,
            target_rr,
            normal_wave,
            normal_metadata,
            normal_rr,
            r_peak_index=estimated_r_peak_index,
        )
        st.pyplot(fig)

    with col_right:
        if target_metadata:
            st.metric("Record", target_metadata["record"])
            st.metric("R-peak sample", f"{target_metadata['r_peak_sample']:,}")
        st.metric("이전 RR 간격", format_rr(target_rr))
        if normal_wave is not None:
            st.metric("비교 정상 RR 간격", format_rr(normal_rr))

    show_probability_table(candidates, label_to_name)

    st.subheader("2단계. 사용자 감별 질문")
    st.write("아래 질문에 답하면 AI 확률과 사용자의 관찰을 결합해 최종 후보를 다시 계산합니다.")
    answers_by_symbol = render_candidate_questions(candidates)

    st.subheader("3단계. 최종 판독 후보")
    final_results = combine_ai_and_user_scores(candidates, answers_by_symbol)
    final_rows = []
    for result in final_results:
        final_rows.append(
            {
                "후보": label_to_name.get(result["label"], result["symbol"]),
                "AI 확률": f"{result['probability']:.1%}",
                "Yes": result["yes_count"],
                "No": result["no_count"],
                "최종 점수": f"{result['final_probability']:.1%}",
            }
        )
    st.table(final_rows)

    best_result = final_results[0]
    rr_text = format_rr(target_rr)
    st.success(make_clinical_summary(best_result, rr_text))

    st.divider()
    st.subheader("이미지 digitization 가이드")
    st.write(
        "- 현재 카메라 입력은 OpenCV 기반 기초 로직으로 검은 ECG trace를 추출합니다.\n"
        "- 실제 임상 이미지에는 종이 회전, 원근 왜곡, lead label, 격자선, 조명 반사가 섞이므로 자동 보정이 추가로 필요합니다.\n"
        "- 최종 앱에서는 1) 종이 영역 검출, 2) perspective 보정, 3) lead별 ROI 분리, 4) grid scale 보정, "
        "5) R-peak 검출, 6) beat segmentation을 순서대로 고도화하면 됩니다.\n"
        "- 현재 모델은 전처리된 단일 beat 입력에 최적화되어 있어, 카메라 이미지는 교육용 프로토타입 판독으로 보아야 합니다."
    )
    render_footer()


if __name__ == "__main__":
    main()
