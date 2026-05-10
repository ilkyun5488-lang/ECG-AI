# 심전도 AI 앱 실행 및 공유 가이드

## 1. 카메라 버튼이 바로 켜지지 않는 이유

`index.html`은 정적 웹페이지입니다. 반면 카메라 AI 판독은 `streamlit_ecg_decision_app.py`라는 Python/Streamlit 서버에서 실행됩니다.

따라서 먼저 Streamlit 서버를 켜야 합니다.

```powershell
.\ecg_cnn_env\Scripts\activate; pip install -r requirements_ecg_app.txt; streamlit run streamlit_ecg_decision_app.py
```

서버가 켜진 뒤 `index.html`의 `카메라로 찾기` 화면에서 `카메라 AI 판독 앱 열기`를 누르면 아래 주소가 열립니다.

```text
http://localhost:8501/?mode=camera
```

## 2. 카카오톡 공유가 안 되는 이유

아래 같은 경로는 내 컴퓨터 안의 파일 위치입니다.

```text
c:\Users\ilkyu\OneDrive\Desktop\...\index.html
```

이 경로를 카카오톡으로 보내도 다른 사람 휴대폰이나 PC에는 같은 파일이 없기 때문에 실행되지 않습니다.

공유하려면 반드시 아래처럼 웹주소가 필요합니다.

```text
https://example.com
```

## 3. 빠른 테스트 공유 방법

내 PC에서 앱을 켠 뒤 임시 HTTPS 주소를 만들려면 ngrok 같은 터널 도구를 사용할 수 있습니다.

```powershell
.\ecg_cnn_env\Scripts\activate; streamlit run streamlit_ecg_decision_app.py
```

다른 터미널에서:

```powershell
ngrok http 8501
```

ngrok이 보여주는 `https://...ngrok-free.app` 주소를 카카오톡으로 공유하면 휴대폰에서 접속할 수 있습니다.

## 4. 정식 공유 방법

장기적으로는 Streamlit 앱을 배포하는 것이 좋습니다.

- Streamlit Community Cloud
- Render
- Hugging Face Spaces
- Azure App Service

이 경우 공유할 주소는 Streamlit 앱 주소 하나면 충분합니다. `index.html`을 따로 보내는 방식보다 안정적입니다.

## 5. 카메라 권한 주의

모바일 브라우저는 보안 때문에 카메라를 보통 `https://` 주소에서만 허용합니다.

예외적으로 내 컴퓨터에서는 `localhost`가 허용됩니다.

즉, 휴대폰에서 카메라 테스트를 하려면 `https://` 배포 주소 또는 ngrok 주소가 필요합니다.
