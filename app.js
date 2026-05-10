/**
 * 간호사를 위한 심전도(부정맥) 학습 앱 - 단일 파일 라우터
 * - 설치 없이 index.html을 열면 동작하도록 순수 JS로 구성
 * - 화면 전환은 location.hash 기반(#/menu, #/algorithm, #/ai)
 */

const routes = {
  "#/menu": renderMenuScreen,
  "#/algorithm": renderAlgorithmScreen,
  "#/ai": renderAiScreen,
};

const STORAGE_KEY = "ecg_algo_state_v1";
const STREAMLIT_CAMERA_URL = "http://localhost:8501/?mode=camera";

function isRemovedQrsPath(state, qrs = state.qrs) {
  return (
    state.regularity === "irregular" &&
    (state.rate === "normal" || state.rate === "brady") &&
    qrs === "wide"
  );
}

const narrowRegularTachyRhythms = [
  {
    name: "동빈맥",
    englishName: "Sinus Tachycardia",
    image: "./assets/user/simus tachycardia.png",
    alt: "동빈맥 심전도 예시",
    description: [
      "쉬운 설명: 심장의 정상 대장인 동결절(SA node)이 단순히 일을 빨리 하고 있는 상태입니다.",
      "기전: 운동, 통증, 발열, 저혈압 등 신체의 요구에 반응하여 심박수가 올라간 상태입니다.",
      "감별 포인트: 정상적인 P-QRS-T 모양을 유지하며, 심박수가 서서히 올라가고 서서히 내려갑니다.",
      "처치: 원인 해결이 우선입니다. 열이 나면 해열제를, 통증이 있으면 진통제를, 수액 부족이면 hydration을 해줍니다. 베타차단제 같은 심장약을 바로 쓰기보다 '왜 빨라졌나?'를 먼저 찾아야 합니다.",
    ],
  },
  {
    name: "심방빈맥",
    englishName: "Atrial Tachycardia",
    image: "./assets/user/atrial tachycardia.png",
    alt: "심방빈맥 심전도 예시",
    description: [
      "쉬운 설명: 동결절이 아닌 심방의 다른 부위가 '내가 대장이다!' 하고 빠르게 전기 신호를 쏘는 상태입니다.",
      "주의사항: 무조건 규칙적이지 않을 수 있습니다. 심방에서 쏘는 신호를 방실결절(AV node)이 다 받아주지 못하면 전도비(2:1, 3:1 등)가 변하면서 불규칙해질 수 있습니다.",
      "처치: 약물 치료(베타차단제, 칼슘통로차단제)를 하거나 심하면 전극도자 절제술을 고려합니다.",
    ],
  },
  {
    name: "심방조동",
    englishName: "Atrial Flutter",
    image: "./assets/user/atrial flutter.png",
    alt: "심방조동 심전도 예시",
    description: [
      "쉬운 설명: 심방 안에서 전기가 뱅글뱅글 맴돌며(회귀) 심방이 분당 250~350회로 매우 빠르게 뛰는 상태입니다.",
      "감별 포인트: 베이스라인이 톱날 모양(Saw-tooth)인 F파가 특징입니다.",
      "주의사항: 전도비에 따라 규칙성이 결정됩니다. 2:1이나 4:1로 일정하게 내려오면 규칙적이지만, 전도비가 수시로 바뀌면(Variable conduction) 매우 불규칙하게 보일 수 있습니다.",
      "처치: 혈전 방지(항응고제)가 중요하며, 리듬 조절을 위해 약물이나 전극도자 절제술을 시행합니다.",
    ],
  },
  {
    name: "AVRT",
    englishName: "방실 회귀성 빈맥",
    image: "./assets/user/AVRT.png",
    alt: "AVRT 심전도 예시",
    description: [
      "쉬운 설명: 심방과 심실 사이에 정상 통로 외에 '샛길(부전도로)'이 하나 더 있어서 전기가 뱅글뱅글 도는 것입니다.",
      "기전: WPW 증후군 환자에게서 흔히 발생합니다.",
      "처치: 아데노신(Adenosine) 투여가 효과적이며, 근본적으로는 샛길을 지지는 절제술이 필요합니다.",
    ],
  },
  {
    name: "AVNRT",
    englishName: "방실결절 회귀성 빈맥",
    image: "./assets/user/AVNRT.png",
    alt: "AVNRT 심전도 예시",
    description: [
      "쉬운 설명: 심장의 정거장인 방실결절(AV node) 안에 길이 '빠른 길'과 '느린 길' 두 개가 생겨 그 안에서 전기가 뱅글뱅글 도는 것입니다.",
      "감별 포인트: PSVT 중 가장 흔한 형태입니다. P파가 QRS 속에 숨어 있거나 바로 뒤에 붙어 있어 잘 안 보입니다.",
      "처치: 아데노신 투여가 표준 처치이며, 발생 시 미주신경 자극(Vagal maneuver, 예: Valsalva)을 먼저 시도해 볼 수 있습니다.",
    ],
  },
];

const wideRegularTachyRhythms = [
  {
    name: "심실빈맥",
    englishName: "Ventricular Tachycardia, VT",
    image: "./assets/user/ventricular tachycardia.png",
    alt: "심실빈맥 심전도 예시",
    description: [
      "핵심 특징: QRS 폭이 0.12초(작은 칸 3칸) 이상으로 넓고, 모양이 일정하지 않거나 비정상적으로 보입니다. 리듬은 대개 매우 규칙적입니다.",
      "기전: 심실 안의 이위성 부위가 빠르게 전기 신호를 만들어 심실을 반복적으로 수축시키는 상태입니다. 정상 전도길을 거치지 않기 때문에 QRS가 넓게 나타납니다.",
      "위험성: 심박출량이 급격히 줄어 혈압 저하, 흉통, 호흡곤란, 의식 저하가 생길 수 있습니다. 방치하면 심실세동(VF)이나 심정지로 진행할 수 있어 치명적인 부정맥으로 봅니다.",
      "가장 먼저 볼 것: 모니터 리듬보다 환자를 먼저 확인합니다. 의식, 맥박, 혈압, 산소포화도, 흉통 여부를 즉시 확인하고 불안정한 상태인지 판단합니다.",
      "불안정한 VT: 혈압 저하, 쇼크, 심한 흉통, 급성 심부전, 의식 저하가 있으면 즉시 의사에게 알리고 동기화 심율동전환(Synchronized Cardioversion)을 준비합니다. 필요 시 아미오다론 같은 항부정맥제가 함께 사용될 수 있습니다.",
      "안정적인 VT: 의식이 있고 혈압이 유지되면 항부정맥제 치료를 고려합니다. 대표적으로 아미오다론, 리도카인이 사용될 수 있으며, 심장내과 평가로 원인을 확인합니다.",
      "무맥성 VT: 의식이 없고 경동맥 맥박이 만져지지 않으면 심정지 상황입니다. 즉시 CPR을 시작하고 제세동(Defibrillation)을 시행합니다.",
      "감별할 리듬: 드물게 SVT에 각차단(LBBB, RBBB)이 동반되어 Wide QRS 빈맥처럼 보일 수 있습니다. 그러나 감별이 어렵다면 Wide QRS 빈맥은 VT로 간주하고 대응하는 것이 안전합니다.",
      "간호사 팁: Wide QRS 빈맥을 보면 먼저 '맥박이 있는가, 의식이 있는가, 혈압이 유지되는가'를 확인합니다. 무맥성이면 코드 블루, 불안정하면 응급 전기 처치 준비가 우선입니다.",
    ],
  },
];

const wideIrregularTachyRhythms = [
  {
    name: "변행전도를 동반한 심방세동",
    englishName: "Atrial Fibrillation with Aberrancy",
    image: "./assets/user/Atrial fibrillation with LBBB.png",
    alt: "변행전도를 동반한 심방세동 심전도 예시",
    description: [
      "쉬운 설명: 심방세동으로 리듬이 불규칙한데, 기존 각차단이나 전도 지연 때문에 QRS가 넓게 보이는 상태입니다.",
      "심전도 특징: R-R 간격이 매우 불규칙하고 P파가 뚜렷하지 않습니다. QRS는 LBBB, RBBB 같은 전도 이상 때문에 넓게 보일 수 있습니다.",
      "감별 포인트: 불규칙한 wide QRS 빈맥은 위험 리듬이 섞여 있을 수 있어 주의합니다. 환자 상태가 불안정하면 즉시 응급 처치 흐름으로 봅니다.",
      "처치: 의식, 맥박, 혈압을 먼저 확인합니다. 안정적이면 원인과 항응고 필요성, rate control 등을 평가하고, 불안정하면 즉시 의료진에게 보고합니다.",
      "간호사 팁: '불규칙 + P파 없음 + wide QRS'이면 단순 SVT로 보지 말고 심방세동과 전도 이상을 함께 생각합니다.",
    ],
  },
  {
    name: "WPW를 동반한 심방세동",
    englishName: "Atrial Fibrillation with WPW Syndrome",
    image: "./assets/user/Atrial fibrillation with WPW.png",
    alt: "WPW를 동반한 심방세동 심전도 예시",
    description: [
      "쉬운 설명: 심방세동 전기 신호가 정상 AV node뿐 아니라 부전도로를 통해 심실로 빠르게 내려가는 위험한 상태입니다.",
      "심전도 특징: 리듬이 매우 불규칙하고 빠르며, QRS 폭과 모양이 beat마다 달라질 수 있습니다. 매우 빠른 wide QRS 빈맥처럼 보입니다.",
      "위험성: 심실로 너무 많은 신호가 내려가면 심실세동으로 진행할 수 있습니다. 응급 리듬으로 생각해야 합니다.",
      "주의할 약: AV node만 느리게 하는 약물은 상황에 따라 위험할 수 있습니다. 처치는 반드시 의료진 지시에 따라 진행합니다.",
      "간호사 팁: WPW가 의심되는 불규칙 wide QRS 빈맥은 바로 보고하고, 환자 상태와 제세동기 준비 여부를 확인합니다.",
    ],
  },
  {
    name: "다형성 심실빈맥",
    englishName: "Polymorphic Ventricular Tachycardia",
    image: "./assets/user/polymorphic ventricular tachycardia.png",
    alt: "다형성 심실빈맥 심전도 예시",
    description: [
      "쉬운 설명: 심실에서 빠른 전기 신호가 나오는데 QRS 모양이 한 가지가 아니라 계속 바뀌는 심실빈맥입니다.",
      "심전도 특징: Wide QRS 빈맥이며 QRS 모양과 높이가 계속 변합니다. 리듬은 불규칙하게 보일 수 있습니다.",
      "위험성: 혈압 저하, 의식 소실, 심실세동으로 진행할 수 있는 매우 위험한 부정맥입니다.",
      "처치: 환자의 맥박과 의식이 가장 중요합니다. 불안정하거나 무맥성이면 ACLS 흐름에 따라 즉시 전기 치료와 CPR 준비가 필요합니다.",
      "간호사 팁: QRS 모양이 계속 바뀌는 wide QRS 빈맥은 모니터 이상으로 넘기지 말고 즉시 환자를 확인합니다.",
    ],
  },
  {
    name: "Torsades de Pointes",
    englishName: "Torsades de Pointes",
    image: "./assets/user/Torsades de Pointes.png",
    alt: "Torsades de Pointes 심전도 예시",
    description: [
      "쉬운 설명: 다형성 심실빈맥의 한 형태로, QRS가 기준선을 중심으로 꼬이듯이 커졌다 작아졌다 보이는 리듬입니다.",
      "심전도 특징: Wide QRS 빈맥이며 QRS 축과 크기가 주기적으로 변합니다. QT 연장과 관련되는 경우가 많습니다.",
      "흔한 원인: 저칼륨혈증, 저마그네슘혈증, QT 연장 약물, 선천성 QT 연장 등이 원인이 될 수 있습니다.",
      "처치: 즉시 환자 상태를 확인하고 의료진에게 보고합니다. 마그네슘 투여, 원인 약물 중단, 전해질 교정, 불안정 시 전기 치료가 고려됩니다.",
      "간호사 팁: '꼬이는 듯한 wide QRS'와 QT 연장을 함께 기억합니다. 실신이나 무맥성이면 응급 상황입니다.",
    ],
  },
  {
    name: "심실세동",
    englishName: "Ventricular Fibrillation",
    image: "./assets/user/ventricular fibrillation.png",
    alt: "심실세동 심전도 예시",
    description: [
      "쉬운 설명: 심실이 제대로 수축하지 못하고 전기적으로 떨기만 하는 심정지 리듬입니다.",
      "심전도 특징: 규칙적인 QRS, P파, T파를 구분할 수 없습니다. 파형이 매우 혼란스럽고 맥박이 없습니다.",
      "위험성: 즉시 치료하지 않으면 사망으로 이어지는 치명적인 리듬입니다.",
      "처치: 환자 반응과 맥박을 즉시 확인합니다. 무맥성이면 CPR을 시작하고 제세동(Defibrillation)을 즉시 시행합니다.",
      "간호사 팁: VF는 분석보다 행동이 먼저입니다. 도움 요청, CPR, 제세동기 준비를 즉시 진행합니다.",
    ],
  },
];

const pacemakerRhythms = [
  {
    name: "VVI Pacemaker",
    englishName: "Ventricular Demand Pacemaker",
    image: "./assets/user/VVI pacemaker.png",
    alt: "VVI pacemaker 심전도 예시",
    description: [
      "쉬운 설명: 심실에 전기 자극을 주는 인공심박동기 리듬입니다. 심박수가 너무 느릴 때 심실을 대신 자극해 박동을 만들 수 있습니다.",
      "심전도 특징: pacing spike가 보이고 그 뒤에 넓은 QRS가 나타납니다. 심실을 직접 자극하므로 QRS가 wide하게 보이는 경우가 많습니다.",
      "작동 방식: 심실을 감지하고, 필요할 때만 심실을 자극합니다. 환자의 자체 박동이 충분하면 기다리고, 느려지면 pacing이 들어갑니다.",
      "간호사 팁: spike 뒤에 QRS가 따라오는지 확인합니다. spike만 있고 QRS가 없으면 capture 문제를 의심합니다.",
    ],
  },
  {
    name: "DDD Pacemaker",
    englishName: "Dual-Chamber Pacemaker",
    image: "./assets/user/DDD pacemaker.png",
    alt: "DDD pacemaker 심전도 예시",
    description: [
      "쉬운 설명: 심방과 심실을 모두 감지하고 필요하면 둘 다 자극할 수 있는 이중방 인공심박동기입니다.",
      "심전도 특징: 심방 pacing spike, 심실 pacing spike가 각각 보일 수 있습니다. 경우에 따라 두 개의 spike가 이어서 보이고 QRS가 뒤따릅니다.",
      "작동 방식: 심방과 심실의 타이밍을 맞춰 심장이 더 자연스럽게 뛰도록 돕습니다.",
      "간호사 팁: spike 위치와 그 뒤의 P파 또는 QRS 반응을 봅니다. 박동기 모드와 환자 맥박이 맞는지 함께 확인합니다.",
    ],
  },
  {
    name: "Failure to Capture",
    englishName: "Pacemaker Malfunction: Failure to Capture",
    image: "./assets/user/failure to capture_ventricle.png",
    alt: "Failure to capture 심전도 예시",
    description: [
      "쉬운 설명: 인공심박동기가 전기 자극은 내보냈지만 심장이 실제로 반응하지 못하는 상태입니다.",
      "심전도 특징: pacing spike는 보이지만 그 뒤에 기대되는 P파나 QRS가 나오지 않습니다.",
      "가능한 원인: lead 위치 문제, 배터리 문제, 전해질 이상, 심근 상태 변화, 출력 부족 등이 원인이 될 수 있습니다.",
      "처치: 환자의 의식, 맥박, 혈압을 즉시 확인하고 의료진에게 보고합니다. 증상이 있으면 응급 pacing/장비 확인이 필요할 수 있습니다.",
      "간호사 팁: spike가 있는지만 보지 말고, spike 뒤에 실제 박동이 생겼는지 확인합니다.",
    ],
  },
  {
    name: "Failure to Pace",
    englishName: "Pacemaker Malfunction: Failure to Pace",
    image: "./assets/user/failure to pace_atrial.png",
    alt: "Failure to pace 심전도 예시",
    description: [
      "쉬운 설명: 인공심박동기가 필요한 순간에 전기 자극을 내보내지 못하는 상태입니다.",
      "심전도 특징: 환자 심박수가 설정된 pacing rate보다 느린데도 pacing spike가 나타나지 않습니다.",
      "가능한 원인: 배터리 소모, lead 문제, 감지 이상, 기기 설정 문제 등이 원인이 될 수 있습니다.",
      "처치: 환자 상태를 먼저 확인하고 즉시 보고합니다. 증상성 서맥이면 산소, IV 확보, 모니터링, 외부 pacing 준비가 필요할 수 있습니다.",
      "간호사 팁: 느린 맥박인데 spike가 안 보이면 failure to pace를 생각합니다.",
    ],
  },
];

const narrowRegularBradyRhythms = [
  {
    name: "동서맥",
    englishName: "Sinus Bradycardia",
    image: "./assets/user/sinus bradycardia.png",
    alt: "동서맥 심전도 예시",
    description: [
      "쉬운 설명: 정상 박동을 만드는 동결절(SA node)이 평소보다 느리게 전기 신호를 보내는 상태입니다.",
      "심전도 특징: 리듬은 규칙적이고, P파가 QRS 앞에 하나씩 보입니다. QRS는 좁고, 심박수는 보통 분당 60회 미만입니다.",
      "흔한 원인: 수면, 운동선수, 미주신경 항진처럼 정상적으로 보일 수 있습니다. 베타차단제, 칼슘통로차단제, 디곡신, 저체온, 갑상샘기능저하, 심근허혈도 원인이 될 수 있습니다.",
      "처치: 증상이 없고 활력징후가 안정적이면 경과 관찰을 합니다. 어지러움, 저혈압, 흉통, 호흡곤란, 의식 저하가 있으면 증상성 서맥으로 보고 즉시 보고하며 산소, IV 확보, 심전도 모니터링, 아트로핀 또는 pacing 준비를 고려합니다.",
      "간호사 팁: 숫자만 보지 말고 환자를 먼저 봅니다. 맥박이 느려도 혈압과 의식이 안정적이면 급하게 약을 쓰지 않을 수 있습니다.",
    ],
  },
  {
    name: "접합부 이탈리듬",
    englishName: "Junctional Escape Rhythm",
    image: "./assets/user/junctional escape rhythm.png",
    alt: "접합부 이탈리듬 심전도 예시",
    description: [
      "쉬운 설명: 동결절이 너무 느리거나 쉬면, 방실접합부(AV junction)가 대신 박동을 만들어 심장을 멈추지 않게 하는 예비 리듬입니다.",
      "심전도 특징: 리듬은 규칙적이고, 심박수는 보통 분당 40~60회입니다. QRS는 대개 좁습니다. P파는 안 보이거나, QRS 앞뒤에 거꾸로 보일 수 있습니다.",
      "기전: 전기 신호가 동결절이 아니라 AV node 주변에서 시작합니다. 그래서 심실로는 정상 길을 따라 내려가 QRS가 좁고, 심방 쪽으로는 거꾸로 전도되어 P파 모양이 달라집니다.",
      "처치: 안정적이고 증상이 없으면 원인을 찾으며 관찰합니다. 약물 영향(디곡신, 베타차단제, 칼슘통로차단제), 허혈, 전해질 이상 등을 확인합니다. 저혈압이나 의식 저하가 있으면 증상성 서맥 처치와 pacing 준비가 필요할 수 있습니다.",
      "간호사 팁: 이 리듬은 몸이 만든 '백업 박동'일 수 있습니다. 무조건 없애려 하지 말고, 환자가 안정적인지와 왜 동결절이 느려졌는지를 먼저 봅니다.",
    ],
  },
  {
    name: "1도 방실차단",
    englishName: "First-Degree AV Block",
    image: "./assets/user/1at degree AV block.png",
    alt: "1도 방실차단 심전도 예시",
    description: [
      "쉬운 설명: 심방에서 심실로 전기가 내려가는 길이 막힌 것은 아니고, 방실결절에서 조금 늦게 지나가는 상태입니다.",
      "심전도 특징: 모든 P파 뒤에 QRS가 따라옵니다. 빠지는 박동은 없습니다. 다만 PR 간격이 0.20초를 초과해 길어져 있습니다.",
      "중요한 점: 1도 방실차단은 심박수가 60회 이하가 아닌 경우도 많지만, 전도 지연과 서맥성 리듬을 함께 공부하기 위해 서맥 카테고리에 넣어 다루기도 합니다.",
      "처치: 대부분 증상이 없고 특별한 치료가 필요하지 않습니다. 원인 약물, 전해질 이상, 심근허혈 여부를 확인하고 주기적으로 심전도를 관찰합니다.",
      "간호사 팁: 핵심은 'PR이 길지만 하나도 빠지지 않는다'입니다. 어지러움, 실신, 흉통이 있거나 PR이 매우 길면 의료진에게 보고합니다.",
    ],
  },
];

const narrowRegularNormalRhythms = [
  {
    name: "정상동율동",
    englishName: "Normal Sinus Rhythm",
    image: "./assets/user/normal sinus rhythm.png",
    alt: "정상동율동 심전도 예시",
    description: [
      "쉬운 설명: 심장의 정상 박동 조율자인 동결절(SA node)에서 규칙적으로 전기 신호가 나오는 정상 리듬입니다.",
      "심전도 특징: 리듬은 규칙적이고 심박수는 분당 60~100회입니다. P파가 QRS 앞에 하나씩 있으며, PR 간격은 보통 0.12~0.20초입니다.",
      "QRS 특징: QRS 폭은 0.12초 미만으로 좁고, 심실 전도가 정상적으로 이루어지고 있음을 의미합니다.",
      "처치: 증상이 없고 활력징후가 안정적이면 특별한 처치가 필요하지 않습니다. 환자 상태와 증상을 함께 확인합니다.",
      "간호사 팁: 정상동율동은 '규칙적, 60~100회, P파가 QRS 앞에 하나씩, Narrow QRS'를 기억하면 됩니다.",
    ],
  },
];

const wideRegularNormalRhythms = [
  {
    name: "우각차단",
    englishName: "Right Bundle Branch Block, RBBB",
    image: "./assets/user/RBBB.png",
    alt: "우각차단 심전도 예시",
    description: [
      "쉬운 설명: 오른쪽 심실로 전기가 내려가는 길이 늦어져 QRS가 넓어지는 상태입니다.",
      "심전도 특징: QRS 폭이 0.12초 이상으로 넓습니다. V1, V2에서 토끼 귀처럼 보이는 rSR' 모양이 보일 수 있습니다.",
      "감별 포인트: V1, V2에서 R'가 두드러지고, I, V6에서는 넓은 S파가 보일 수 있습니다.",
      "처치: 증상이 없고 기존에 있던 RBBB라면 관찰할 수 있습니다. 새로 생긴 흉통, 호흡곤란, 실신이 있으면 즉시 보고합니다.",
      "간호사 팁: Wide QRS라도 규칙적이고 심박수가 정상 범위라면 각차단 여부를 함께 확인합니다.",
    ],
  },
  {
    name: "좌각차단",
    englishName: "Left Bundle Branch Block, LBBB",
    image: "./assets/user/LBBB.png",
    alt: "좌각차단 심전도 예시",
    description: [
      "쉬운 설명: 왼쪽 심실로 전기가 내려가는 길이 늦어져 QRS가 넓어지는 상태입니다.",
      "심전도 특징: QRS 폭이 0.12초 이상이고, V1에서는 깊은 S파 또는 QS 모양, I, aVL, V5, V6에서는 넓고 둔한 R파가 보일 수 있습니다.",
      "감별 포인트: LBBB가 새로 생겼거나 흉통이 동반되면 허혈성 심질환 평가가 중요합니다.",
      "처치: 기존 LBBB인지 새로 생긴 LBBB인지 확인합니다. 흉통, 저혈압, 호흡곤란이 있으면 즉시 보고합니다.",
      "간호사 팁: LBBB에서는 심근경색 판독이 어려울 수 있으므로 증상과 활력징후를 함께 봅니다.",
    ],
  },
  {
    name: "WPW 증후군",
    englishName: "Wolff-Parkinson-White Syndrome",
    image: "./assets/user/WPW.png",
    alt: "WPW 증후군 심전도 예시",
    description: [
      "쉬운 설명: 심방과 심실 사이에 정상 길 외에 샛길(부전도로)이 있어 전기가 심실로 조금 빨리 내려가는 상태입니다.",
      "심전도 특징: PR 간격이 짧고, QRS 시작 부분이 둔하게 올라가는 delta wave가 보입니다. QRS는 넓어질 수 있습니다.",
      "감별 포인트: WPW가 있는 환자는 AVRT 같은 발작성 빈맥이 생길 수 있고, 심방세동이 동반되면 위험할 수 있습니다.",
      "처치: 증상이 없으면 외래 평가로 확인할 수 있습니다. 두근거림, 실신, 빠른 불규칙 wide QRS 빈맥이 있으면 즉시 보고합니다.",
      "간호사 팁: 짧은 PR과 delta wave를 같이 찾습니다. WPW 의심 환자의 빠른 부정맥은 약물 선택에 주의가 필요합니다.",
    ],
  },
];

const narrowIrregularNormalRhythms = [
  {
    name: "이동성 심방박동",
    englishName: "Wandering Atrial Pacemaker",
    image: "./assets/user/wandering atrial pacemaker.png",
    alt: "이동성 심방박동 심전도 예시",
    description: [
      "쉬운 설명: 심방 안에서 박동을 시작하는 위치가 조금씩 바뀌는 리듬입니다. 동결절 하나가 계속 지휘하는 것이 아니라, 여러 심방 부위가 번갈아 신호를 내는 모습입니다.",
      "심전도 특징: 심박수는 보통 60~100회입니다. P파 모양이 최소 3가지 이상으로 달라지고, PR 간격도 조금씩 변합니다. QRS는 대개 좁습니다.",
      "감별 포인트: 빠르지 않으면 Wandering Atrial Pacemaker, 100회 이상으로 빨라지면 Multifocal Atrial Tachycardia 쪽을 생각합니다.",
      "처치: 증상이 없으면 대개 특별한 치료 없이 관찰합니다. 저산소증, 폐질환, 전해질 이상, 약물 영향 같은 원인이 있는지 확인합니다.",
      "간호사 팁: 핵심은 'P파 모양이 여러 가지인데 QRS는 좁다'입니다. 환자가 안정적인지 먼저 확인합니다.",
    ],
  },
  {
    name: "동성 부정맥",
    englishName: "Sinus Arrhythmia",
    image: "./assets/user/sinus arrhythmia.png",
    alt: "동성 부정맥 심전도 예시",
    description: [
      "쉬운 설명: 동결절에서 나온 정상 리듬이지만, 호흡에 따라 박동 간격이 조금 빨라졌다 느려졌다 하는 상태입니다.",
      "심전도 특징: P파가 QRS 앞에 하나씩 있고 P파 모양은 일정합니다. QRS는 좁습니다. 다만 R-R 간격이 규칙적이지 않게 조금씩 변합니다.",
      "감별 포인트: 흡기 때 심박수가 빨라지고 호기 때 느려지는 호흡성 동성 부정맥이 흔합니다. 젊은 사람이나 건강한 사람에게서도 볼 수 있습니다.",
      "처치: 증상이 없고 활력징후가 안정적이면 치료가 필요하지 않습니다. 어지러움, 흉통, 실신 같은 증상이 있으면 다른 원인을 함께 확인합니다.",
      "간호사 팁: 불규칙해 보여도 P파가 일정하게 QRS 앞에 붙어 있으면 동성 리듬인지 먼저 봅니다.",
    ],
  },
];

const narrowIrregularTachyRhythms = [
  {
    name: "심방조기수축",
    englishName: "Premature Atrial Contraction, PAC",
    image: "./assets/user/PAC.png",
    alt: "심방조기수축 심전도 예시",
    description: [
      "쉬운 설명: 정상 박동보다 조금 이른 타이밍에 심방에서 전기 신호가 먼저 튀어나오는 상태입니다.",
      "심전도 특징: 예상보다 빠른 P파가 먼저 나오고, 그 뒤에 QRS가 따라옵니다. QRS는 보통 좁습니다. 조기 P파 모양은 정상 P파와 다르게 보일 수 있습니다.",
      "흔한 원인: 카페인, 스트레스, 수면 부족, 음주, 흡연, 전해질 이상, 심장질환 등에서 보일 수 있습니다.",
      "처치: 드물고 증상이 없으면 대개 관찰합니다. 빈번하거나 두근거림이 심하면 원인 교정, 활력징후 확인, 필요 시 의료진 보고가 필요합니다.",
      "간호사 팁: PAC는 '정상 박동 사이에 일찍 끼어든 심방 박동'으로 이해하면 쉽습니다.",
    ],
    subtypes: [
      {
        name: "PAC Bigeminy",
        image: "./assets/user/PAC bigeminy.png",
        alt: "PAC bigeminy 심전도 예시",
        description: [
          "정상 박동과 PAC가 번갈아 나오는 형태입니다. 즉, 두 박동마다 한 번씩 PAC가 끼어드는 양상입니다.",
          "비슷하게 PAC가 3번에 한 번씩 나오면 trigeminy라고 부릅니다. 규칙적으로 반복되는 조기수축 패턴을 볼 때 함께 기억하면 좋습니다.",
        ],
      },
      {
        name: "Non-conducted APC",
        image: "./assets/user/non-conducted APC.png",
        alt: "전도되지 않은 APC 심전도 예시",
        description: [
          "조기 심방수축이 너무 빨리 와서 AV node가 아직 준비되지 않은 경우입니다.",
          "P파는 보이지만 QRS가 따라오지 않아 박동이 빠진 것처럼 보일 수 있습니다. 서맥이나 차단으로 오해하지 않도록 조기 P파를 찾아야 합니다.",
        ],
      },
      {
        name: "Aberrant Conduction",
        image: "./assets/user/aberrant conduction.png",
        alt: "변행전도를 동반한 PAC 심전도 예시",
        description: [
          "PAC가 심실로 내려가기는 하지만, 전도계 일부가 아직 회복되지 않아 QRS가 넓게 보이는 형태입니다.",
          "겉으로는 PVC처럼 보일 수 있으나, 앞에 조기 P파가 있으면 PAC with aberrant conduction을 생각합니다.",
        ],
      },
    ],
  },
  {
    name: "빈맥-서맥 증후군",
    englishName: "Tachy-brady Syndrome",
    image: "./assets/user/tachy-brady syndrome.png",
    alt: "빈맥-서맥 증후군 심전도 예시",
    description: [
      "쉬운 설명: 빠른 심방성 리듬이 나타나다가 갑자기 긴 pause나 서맥이 이어지는 상태입니다. 동결절 기능이 약해진 sick sinus syndrome의 한 형태로 이해하면 쉽습니다.",
      "심전도 특징: 빠른 리듬 뒤에 박동이 한동안 멈춘 것처럼 보이는 sinus pause가 생길 수 있습니다. QRS는 대개 좁고, R-R 간격은 매우 불규칙합니다.",
      "감별 포인트: 단순 PAC나 동성 부정맥보다 pause가 길고 증상과 연결될 수 있습니다. 어지러움, 실신, 식은땀, 저혈압이 동반되는지 확인합니다.",
      "처치: 증상이 있거나 pause가 길면 즉시 의료진에게 보고합니다. 약물, 전해질 이상, 허혈 여부를 확인하고 필요 시 pacemaker 평가가 필요할 수 있습니다.",
      "간호사 팁: 모니터에서 빠르게 뛰다가 갑자기 길게 쉬는 패턴이 보이면 환자의 의식, 맥박, 혈압을 먼저 확인합니다.",
    ],
  },
];

const narrowIrregularBradyRhythms = [
  {
    name: "2도 방실차단 1형",
    englishName: "Second-Degree AV Block Type I, Wenckebach",
    image: "./assets/user/2nd degree AV block Mobits Type 1.png",
    alt: "2도 방실차단 1형 심전도 예시",
    description: [
      "쉬운 설명: 심방에서 심실로 전기가 내려가다가 점점 늦어지고, 결국 한 번은 심실로 전달되지 못하는 상태입니다.",
      "심전도 특징: PR 간격이 점점 길어지다가 QRS가 한 번 빠집니다. 그 뒤 다시 같은 패턴이 반복됩니다.",
      "감별 포인트: '점점 길어지다가 하나 빠진다'가 핵심입니다. QRS는 대개 좁고, AV node 수준의 전도 지연인 경우가 많습니다.",
      "처치: 증상이 없고 안정적이면 관찰하는 경우가 많습니다. 어지러움, 저혈압, 흉통, 의식 저하가 있으면 증상성 서맥으로 보고 즉시 보고합니다.",
      "간호사 팁: 빠진 QRS만 보지 말고, 빠지기 전 PR 간격이 점점 길어지는지 확인합니다.",
    ],
  },
  {
    name: "2도 방실차단 2형",
    englishName: "Second-Degree AV Block Type II",
    image: "./assets/user/2nd degree AV block Mobits Type 2.png",
    alt: "2도 방실차단 2형 심전도 예시",
    description: [
      "쉬운 설명: 전기가 잘 내려가다가 예고 없이 심실로 전달되지 않아 QRS가 빠지는 상태입니다.",
      "심전도 특징: PR 간격은 일정한데 갑자기 QRS가 빠집니다. P파는 보이지만 뒤따르는 QRS가 없는 박동이 생깁니다.",
      "감별 포인트: 1형과 달리 PR이 점점 길어지지 않습니다. 갑자기 빠지는 QRS가 핵심입니다.",
      "위험성: 3도 방실차단으로 진행할 수 있어 더 위험하게 봅니다. 증상이 없어도 의료진 보고와 모니터링이 중요합니다.",
      "간호사 팁: Mobitz II는 '예고 없이 빠진다'로 기억합니다. pacing 필요성을 염두에 둡니다.",
    ],
  },
  {
    name: "고도 방실차단",
    englishName: "High-Degree AV Block",
    image: "./assets/user/High degree AV block.png",
    alt: "고도 방실차단 심전도 예시",
    description: [
      "쉬운 설명: 심방의 전기 신호 여러 개 중 일부만 심실로 내려가는 심한 방실차단입니다.",
      "심전도 특징: P파는 여러 번 보이지만 QRS는 드물게 나타납니다. 예를 들어 2:1, 3:1처럼 여러 P파 중 하나만 전도될 수 있습니다.",
      "위험성: 심실 박동이 느려져 심박출량이 감소할 수 있고, 완전 방실차단으로 진행할 수 있습니다.",
      "처치: 즉시 환자의 의식, 맥박, 혈압을 확인하고 심전도 모니터링을 유지합니다. 불안정하면 pacing 준비가 필요합니다.",
      "간호사 팁: P파는 많은데 QRS가 적으면 고도 방실차단을 생각하고 바로 보고합니다.",
    ],
  },
  {
    name: "동방출구차단",
    englishName: "SA Exit Block",
    image: "./assets/user/sinus exit block.png",
    alt: "동방출구차단 심전도 예시",
    description: [
      "쉬운 설명: 동결절에서 전기 신호는 만들어졌지만, 그 신호가 심방으로 잘 나오지 못해 박동이 빠지는 상태입니다.",
      "심전도 특징: 정상 동성 박동 중간에 P-QRS-T가 통째로 빠지는 pause가 생깁니다. pause 길이가 기본 PP 간격의 배수처럼 보일 수 있습니다.",
      "감별 포인트: sinus pause와 비슷하지만, SA exit block은 빠진 간격이 원래 주기의 배수 관계를 보이는 경우가 많습니다.",
      "처치: 증상이 없으면 관찰할 수 있으나, 어지러움·실신·저혈압이 있으면 증상성 서맥으로 보고합니다.",
      "간호사 팁: '박동 한 세트가 통째로 빠졌는지'와 pause 길이를 확인합니다.",
    ],
  },
  {
    name: "동정지",
    englishName: "Sinus Arrest",
    image: "./assets/user/sinus pause.png",
    alt: "동정지 심전도 예시",
    description: [
      "쉬운 설명: 동결절이 잠시 전기 신호를 만들지 않아 박동이 멈춘 것처럼 쉬는 상태입니다.",
      "심전도 특징: P파와 QRS가 한동안 나타나지 않는 pause가 생깁니다. pause 길이는 원래 PP 간격의 정확한 배수로 맞지 않는 경우가 많습니다.",
      "위험성: pause가 길면 어지러움, 실신, 저혈압이 생길 수 있습니다. 긴 pause나 반복되는 pause는 중요하게 봅니다.",
      "처치: 환자 증상과 활력징후를 확인하고 의료진에게 보고합니다. 증상이 있으면 산소, IV 확보, 모니터링, pacing 준비를 고려합니다.",
      "간호사 팁: 긴 pause를 보면 먼저 환자 의식과 맥박을 확인합니다. 모니터 파형보다 환자 상태가 우선입니다.",
    ],
  },
];

const wideRegularBradyRhythms = [
  {
    name: "3도 방실차단",
    englishName: "Third-Degree AV Block",
    image: "./assets/user/3rd degree AV Block.png",
    alt: "3도 방실차단 심전도 예시",
    description: [
      "쉬운 설명: 심방의 전기 신호가 심실로 전혀 내려가지 못하는 완전 방실차단입니다. 심방과 심실이 서로 따로 뛰는 상태입니다.",
      "심전도 특징: P파와 QRS가 각각 규칙적으로 보이지만 서로 관계가 없습니다. PR 간격이 일정하지 않고, 심실 박동수는 대개 느립니다. 탈출리듬 위치에 따라 QRS는 좁거나 넓을 수 있습니다.",
      "위험성: 심박출량이 줄어 저혈압, 어지러움, 실신, 흉통, 호흡곤란이 생길 수 있습니다. 방치하면 심정지로 진행할 수 있어 중요한 응급 리듬입니다.",
      "처치: 즉시 환자의 의식, 맥박, 혈압을 확인하고 심전도 모니터링을 유지합니다. 불안정하면 경피적 pacing을 준비하고, 필요 시 도파민·에피네프린 같은 약물 보조를 고려합니다. 대부분은 심장내과 평가와 인공심박동기 삽입이 필요합니다.",
      "간호사 팁: 3도 방실차단은 'P와 QRS가 따로 논다'가 핵심입니다. 발견하면 단순 관찰로 넘기지 말고 즉시 보고하고 pacing 가능성을 염두에 둡니다.",
    ],
  },
  {
    name: "심실 이탈리듬",
    englishName: "Ventricular Escape Rhythm",
    image: "./assets/user/ventricular escape rhythm.png",
    alt: "심실 이탈리듬 심전도 예시",
    description: [
      "쉬운 설명: 위쪽 박동 명령이 너무 느리거나 내려오지 않을 때, 심실이 마지막 예비 박동원처럼 스스로 느리게 뛰는 상태입니다.",
      "심전도 특징: 리듬은 대개 규칙적이고, 심박수는 보통 분당 20~40회로 매우 느립니다. QRS는 0.12초 이상으로 넓고 모양이 비정상적으로 보입니다.",
      "기전: 전기 신호가 심실 안에서 시작하므로 정상 전도길을 타지 못합니다. 그래서 QRS가 넓고, 박동수도 접합부 이탈리듬보다 더 느립니다.",
      "위험성: 심박출량이 크게 줄어 저혈압, 어지러움, 실신, 의식 저하가 생길 수 있습니다. 심정지 직전의 불안정한 리듬으로 볼 수 있어 빠른 평가가 필요합니다.",
      "처치: 즉시 의식, 맥박, 혈압을 확인하고 의료진에게 보고합니다. 증상성 서맥이면 산소 공급, IV 확보, 심전도 모니터링을 유지하며 경피적 pacing과 응급 약물 준비를 고려합니다.",
      "간호사 팁: Wide QRS에 심박수가 매우 느리면 위험 신호입니다. 모니터만 보지 말고 환자의 맥박과 의식부터 확인합니다.",
    ],
  },
];

function loadAlgoState() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return { step: "q1", regularity: null, rate: null, qrs: null };
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object")
      return { step: "q1", regularity: null, rate: null, qrs: null };
    const state = {
      step: parsed.step ?? "q1",
      regularity: parsed.regularity ?? null,
      rate: parsed.rate ?? null,
      qrs: parsed.qrs ?? null,
    };
    if (isRemovedQrsPath(state)) return { ...state, step: "q3", qrs: null };
    return state;
  } catch {
    return { step: "q1", regularity: null, rate: null, qrs: null };
  }
}

function saveAlgoState(state) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function resetAlgo() {
  saveAlgoState({ step: "q1", regularity: null, rate: null, qrs: null });
  render();
}

function goAlgoBack() {
  const state = loadAlgoState();

  if (state.step === "rhythm") {
    saveAlgoState({ step: "q1", regularity: null, rate: null, qrs: null });
  } else if (state.step === "q2") {
    saveAlgoState({ step: "rhythm", regularity: null, rate: null, qrs: null });
  } else if (state.step === "st" || state.step === "pacemaker") {
    saveAlgoState({ step: "q1", regularity: null, rate: null, qrs: null });
  } else if (state.step === "q3") {
    saveAlgoState({ ...state, step: "q2", rate: null, qrs: null });
  } else if (state.step === "summary") {
    saveAlgoState({ ...state, step: "q3", qrs: null });
  }

  render();
}

function setAlgoAnswer(partial) {
  const prev = loadAlgoState();
  saveAlgoState({ ...prev, ...partial });
}

function $(selector) {
  const el = document.querySelector(selector);
  if (!el) throw new Error(`요소를 찾을 수 없습니다: ${selector}`);
  return el;
}

function navigate(hash) {
  if (location.hash === hash) {
    render();
    return;
  }
  location.hash = hash;
}

function render() {
  const root = $("#root");
  const hash = location.hash || "#/menu";
  const view = routes[hash] ?? routes["#/menu"];
  root.innerHTML = view();

  // 화면별 이벤트 바인딩
  bindCommonActions();
  if (hash === "#/menu") bindMenuActions();
  if (hash === "#/algorithm") bindAlgorithmActions();
  if (hash === "#/ai") bindAiActions();
}

function bindCommonActions() {
  document.querySelectorAll("[data-nav]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.getAttribute("data-nav");
      if (target) navigate(target);
    });
  });
}

function renderMenuScreen() {
  return `
    <section class="card hero">
      <div class="hero__kicker">심전도 교육 앱</div>
      <h1 class="hero__title">심전도 판독 학습을 시작합니다</h1>
      <div class="hero__desc">
        이 앱은 심전도 학습을 돕기 위한 <b>교육용 참고 자료</b>입니다.<br/>
        실제 진단이나 치료 결정은 환자 상태와 전문가 판단을 따라야 합니다.
      </div>
    </section>

    <section class="grid" aria-label="메뉴">
      <button class="menu-btn" type="button" data-start-learning>
        <div class="row">
          <div class="menu-btn__title">
            1. 심전도 학습
            <span class="badge badge--accent">시작</span>
          </div>
          <div class="badge">시작</div>
        </div>
        <div class="menu-btn__desc">
          리듬 알고리즘, ST 변화, Pacemaker 관련 심전도를 단계별로 학습합니다.
        </div>
      </button>

      <button class="menu-btn" type="button" data-nav="#/ai">
        <div class="row">
          <div class="menu-btn__title">
            2. 카메라로 찾기
            <span class="badge badge--accent">AI</span>
          </div>
          <div class="badge">실행</div>
        </div>
        <div class="menu-btn__desc">
          Streamlit AI 판독 앱을 열고, 카메라로 촬영한 심전도를 참고용으로 분석합니다.
        </div>
      </button>
    </section>
  `;
}

function bindMenuActions() {
  document.querySelectorAll("[data-start-learning]").forEach((btn) => {
    btn.addEventListener("click", () => {
      saveAlgoState({ step: "q1", regularity: null, rate: null, qrs: null });
      navigate("#/algorithm");
    });
  });
}

function renderAlgorithmScreen() {
  const state = loadAlgoState();
  const step = state.step ?? "q1";
  const showBackButton = step !== "q1";

  return `
    <div class="toolbar">
      <button class="link" type="button" data-nav="#/menu">← 메뉴로</button>
      ${
        showBackButton
          ? `<button class="link" type="button" data-action="algo-back">← 이전 단계</button>`
          : ""
      }
      <button class="link" type="button" data-action="algo-reset">처음부터</button>
    </div>

    <div class="screen-title">심전도 학습</div>
    ${renderAlgoStep(step)}
  `;
}

function bindAlgorithmActions() {
  document.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.getAttribute("data-action");
      if (action === "algo-reset") resetAlgo();
      if (action === "algo-back") goAlgoBack();
    });
  });

  document.querySelectorAll("[data-step]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const next = btn.getAttribute("data-step");
      if (!next) return;
      setAlgoAnswer({ step: next });
      render();
    });
  });

  document.querySelectorAll("[data-set-regularity]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const v = btn.getAttribute("data-set-regularity");
      if (!v) return;
      // 규칙성 선택 후: 빈맥/서맥 질문으로
      setAlgoAnswer({ regularity: v, step: "q2", rate: null, qrs: null });
      render();
    });
  });

  document.querySelectorAll("[data-set-category]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const v = btn.getAttribute("data-set-category");
      if (!v) return;
      saveAlgoState({ step: v, regularity: null, rate: null, qrs: null });
      render();
    });
  });

  document.querySelectorAll("[data-set-rate]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const v = btn.getAttribute("data-set-rate");
      if (!v) return;
      // 빈맥/서맥 선택 후: QRS 폭 질문으로
      setAlgoAnswer({ rate: v, step: "q3", qrs: null });
      render();
    });
  });

  document.querySelectorAll("[data-set-qrs]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const v = btn.getAttribute("data-set-qrs");
      if (!v) return;
      const state = loadAlgoState();
      if (isRemovedQrsPath(state, v)) {
        setAlgoAnswer({ step: "q3", qrs: null });
        render();
        return;
      }
      // QRS 폭 선택 후: 요약 화면(다음 단계에서 리듬 후보 매핑 예정)
      setAlgoAnswer({ qrs: v, step: "summary" });
      render();
    });
  });

  bindImageZoomActions();
}

function bindImageZoomActions() {
  const modal = document.querySelector("[data-image-modal]");
  if (!modal) return;

  const image = modal.querySelector("[data-modal-image]");
  const title = modal.querySelector("[data-modal-title]");
  const closeBtn = modal.querySelector("[data-modal-close]");

  const closeModal = () => {
    modal.setAttribute("hidden", "");
    image.removeAttribute("src");
    image.removeAttribute("alt");
  };

  document.querySelectorAll("[data-zoom-src]").forEach((thumb) => {
    const openModal = (event) => {
      event.preventDefault();
      event.stopPropagation();

      image.src = thumb.getAttribute("data-zoom-src");
      image.alt = thumb.getAttribute("alt") || "확대된 심전도 사진";
      title.textContent = thumb.getAttribute("data-zoom-title") || "심전도 사진";
      modal.removeAttribute("hidden");
      closeBtn.focus();
    };

    thumb.addEventListener("click", openModal);
    thumb.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") openModal(event);
    });
  });

  modal.addEventListener("click", (event) => {
    if (event.target === modal || event.target.hasAttribute("data-modal-close")) {
      closeModal();
    }
  });

  modal.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeModal();
  });
}

function renderAlgoStep(step) {
  switch (step) {
    case "q1":
      return renderQ1();
    case "rhythm":
      return renderRhythmAlgorithmStart();
    case "q2":
      return renderQ2();
    case "q3":
      return renderQ3();
    case "summary":
      return renderSummary();
    case "st":
      return renderStScreen();
    case "pacemaker":
      return renderPacemakerResults();
    default:
      return renderQ1();
  }
}

function renderQ1() {
  return `
    <section class="card hero">
      <div class="hero__kicker">심전도 학습</div>
      <h2 class="hero__title" style="font-size: 18px; margin: 0;">학습할 영역을 선택하세요</h2>
      <div class="hero__desc">
        리듬 판독 알고리즘, ST 변화, Pacemaker 관련 심전도를 나누어 학습합니다.
      </div>
    </section>

    <div class="choice-grid" role="group" aria-label="심전도 학습 영역 선택">
      <div class="choice-card">
        <div class="choice-card__header">
          <div class="choice-card__title">1. 리듬 알고리즘으로 찾기</div>
          <span class="badge badge--accent">추천</span>
        </div>
        <div class="note">규칙성, 심박수 범주, QRS 폭을 따라가며 후보 리듬을 좁힙니다.</div>
        <button class="primary" type="button" data-set-category="rhythm">선택</button>
      </div>

      <div class="choice-card">
        <div class="choice-card__header">
          <div class="choice-card__title">2. ST 변화 보기</div>
          <span class="badge">준비중</span>
        </div>
        <div class="note">ST elevation, ST depression, T파 변화 등 허혈 관련 소견을 따로 정리합니다.</div>
        <button class="primary" type="button" data-set-category="st">선택</button>
      </div>

      <div class="choice-card">
        <div class="choice-card__header">
          <div class="choice-card__title">3. Pacemaker 리듬 보기</div>
          <span class="badge badge--accent">보기</span>
        </div>
        <div class="note">VVI, DDD, capture failure, pacing failure를 따로 확인합니다.</div>
        <button class="primary" type="button" data-set-category="pacemaker">선택</button>
      </div>
    </div>
  `;
}

function renderRhythmAlgorithmStart() {
  return `
    <section class="card hero">
      <div class="hero__kicker">리듬 알고리즘</div>
      <h2 class="hero__title" style="font-size: 18px; margin: 0;">리듬은 규칙적인가요?</h2>
      <div class="hero__desc">
        먼저 R-R 간격이 일정한지 확인합니다. 이후 심박수와 QRS 폭으로 후보 리듬을 좁힙니다.
      </div>
    </section>

    <div class="choice-grid" role="group" aria-label="규칙성 선택">
      <div class="choice-card">
        <div class="choice-card__header">
          <div class="choice-card__title">규칙</div>
          <span class="badge badge--accent">리듬</span>
        </div>
        <img class="ecg-thumb" src="./assets/user/ecg_regular.png" alt="규칙적인 리듬 예시 심전도" onerror="this.onerror=null;this.src='./assets/ecg_nsr.svg';" />
        <div class="note">R-R 간격이 일정한 리듬입니다.</div>
        <button class="primary" type="button" data-set-regularity="regular">선택</button>
      </div>

      <div class="choice-card">
        <div class="choice-card__header">
          <div class="choice-card__title">불규칙</div>
          <span class="badge badge--danger">리듬</span>
        </div>
        <img class="ecg-thumb" src="./assets/user/ecg_irregular.png" alt="불규칙한 리듬 예시 심전도" onerror="this.onerror=null;this.src='./assets/ecg_af.svg';" />
        <div class="note">R-R 간격이 일정하지 않은 리듬입니다.</div>
        <button class="primary" type="button" data-set-regularity="irregular">선택</button>
      </div>
    </div>
  `;
}

const stRelatedRhythms = [
  {
    name: "Long QT",
    englishName: "Long QT Syndrome",
    image: "./assets/user/long QT.png",
    alt: "Long QT 심전도 예시",
    description: [
      "쉬운 설명: QT 간격이 길어져 심실이 전기적으로 회복되는 시간이 늦어진 상태입니다. 겉으로는 리듬이 비교적 안정적으로 보여도 위험한 심실성 부정맥으로 이어질 수 있습니다.",
      "심전도 특징: QT 또는 QTc가 길게 보입니다. 일반적으로 QTc가 남성 450ms 이상, 여성 460ms 이상이면 길다고 보며, 500ms 이상이면 위험도가 커집니다.",
      "위험성: Torsades de Pointes 같은 다형성 심실빈맥으로 진행할 수 있고, 실신이나 돌연심장사의 원인이 될 수 있습니다.",
      "확인 포인트: 저칼륨혈증, 저마그네슘혈증, 항부정맥제, 일부 항생제, 항정신병약 등 QT 연장 약물을 함께 확인합니다.",
      "간호사 팁: Long QT가 보이면 전해질 결과와 투약 목록을 확인하고, 실신·두근거림·어지러움이 있으면 즉시 보고합니다.",
    ],
  },
  {
    name: "Brugada pattern",
    englishName: "Brugada Pattern",
    image: "./assets/user/Brugada pattern.png",
    alt: "Brugada pattern 심전도 예시",
    description: [
      "쉬운 설명: V1-V2에서 특징적인 ST elevation처럼 보이는 패턴입니다. 급성 심근경색과 달리 유전성 전기 이상과 관련될 수 있습니다.",
      "심전도 특징: 오른쪽 흉부유도 V1-V2에서 coved type ST elevation과 음성 T파가 이어지는 모양을 볼 수 있습니다.",
      "위험성: 심실세동이나 돌연사의 위험 신호가 될 수 있어, 단순 ST 변화로만 넘기지 않아야 합니다.",
      "확인 포인트: 발열, 특정 약물, 전해질 이상이 Brugada pattern을 더 뚜렷하게 만들 수 있습니다. 실신 병력이나 가족력도 중요합니다.",
      "간호사 팁: 의심되면 활력징후와 의식 상태를 확인하고 모니터링을 유지하며 의료진에게 보고합니다. 특히 발열이 있으면 적극적으로 조절합니다.",
    ],
  },
];

function renderStScreen() {
  return `
    <section class="card hero result-guide">
      <div class="hero__kicker">ST 관련</div>
      <div class="result-title">ST Elevation MI 위치 찾기</div>
      <div class="result-sub">
        ST elevation이 어느 lead에서 보이는지 클릭해 보세요. 전극이 바라보는 심장 부위와 의심되는 경색 위치를 연결해 볼 수 있습니다.
      </div>
    </section>

    <section class="card st-mi-card">
      <img
        class="st-mi-image"
        src="./assets/user/ST elevation MI.png"
        alt="ST elevation MI 12유도 심전도 예시"
        role="button"
        tabindex="0"
        data-zoom-src="./assets/user/ST elevation MI.png"
        data-zoom-title="ST Elevation MI"
      />
      <div class="st-mi-text">
        <div class="st-mi-title">ST elevation MI</div>
        <p>
          ST elevation은 심근 손상이 심장 벽의 안쪽에서 바깥쪽까지 진행될 때 나타나는 중요한 소견입니다.
          한 lead만 보지 말고, 서로 같은 심장 벽을 바라보는 lead 묶음에서 함께 올라가는지 확인합니다.
        </p>
        <a class="st-mi-link" href="https://www.3decgleads.com/3d-leads" target="_blank" rel="noreferrer">
          3D ECG Leads에서 lead와 혈관 위치 보기
        </a>
      </div>
    </section>

    <section class="card st-3d-card">
      <div class="st-mi-text">
        <div class="st-mi-title">3D 심장 그림으로 보는 STEMI 위치</div>
        <p>
          아래 3D ECG Leads 자료는 12유도 심전도 lead가 심장의 어느 벽을 바라보는지,
          그리고 그 부위가 어떤 관상동맥 영역과 연결되는지 입체적으로 이해하도록 도와줍니다.
        </p>
        <p>
          핵심은 <b>ST elevation이 한 lead만 올라가는지</b>가 아니라,
          <b>같은 심장 벽을 바라보는 연속된 lead 묶음에서 함께 올라가는지</b>를 보는 것입니다.
          예를 들어 II, III, aVF가 함께 올라가면 하벽, V3-V4가 함께 올라가면 전벽 손상을 먼저 생각합니다.
        </p>
        <a class="st-mi-link" href="https://www.3decgleads.com/3d-leads" target="_blank" rel="noreferrer">
          3D ECG Leads 원본 페이지 열기
        </a>
      </div>
      <div class="st-3d-frame-wrap">
        <iframe
          class="st-3d-frame"
          src="https://www.3decgleads.com/3d-leads"
          title="3D ECG Leads - leads and corresponding vessels in 3D"
          loading="lazy"
        ></iframe>
      </div>
      <div class="note st-3d-note">
        만약 위 3D 심장 그림이 보이지 않으면, 외부 사이트의 보안 정책 때문에 앱 안에서 표시가 차단된 것입니다.
        이 경우 <b>3D ECG Leads 원본 페이지 열기</b> 버튼으로 새 창에서 확인해 주세요.
      </div>
    </section>

    <section class="card st-stemi-detail">
      <div class="st-mi-title">STEMI를 볼 때의 판독 흐름</div>
      <p>
        STEMI는 관상동맥이 급격히 막혀 심근 손상이 심장 벽의 안쪽에서 바깥쪽까지 진행될 때 나타나는 응급 소견입니다.
        심전도에서는 손상 부위를 바라보는 lead에서 ST elevation이 나타나고, 반대편 lead에서는 reciprocal ST depression이 보일 수 있습니다.
      </p>
      <p>
        판독은 <b>lead 묶음 → 심장 벽 → 관련 혈관 → 환자 상태</b> 순서로 연결하면 쉽습니다.
        하벽 STEMI에서는 서맥, 저혈압, 우심실 침범을 함께 확인하고, 전벽 STEMI에서는 손상 범위가 커 심부전이나 쇼크 위험을 더 주의합니다.
      </p>
    </section>

    <div class="st-lead-map" aria-label="ST elevation 부위별 경색 위치">
      <details class="st-lead-card">
        <summary>
          <span class="st-lead-card__leads">II, III, aVF</span>
          <span class="st-lead-card__title">하벽 경색 Inferior MI</span>
        </summary>
        <p>심장의 아래쪽 벽을 보는 lead입니다. ST elevation이 함께 보이면 하벽 심근경색을 의심합니다.</p>
        <p>관련 혈관은 보통 RCA가 많고, 일부에서는 LCx가 원인이 될 수 있습니다. 서맥, 저혈압, 우심실 침범 여부를 함께 봅니다.</p>
      </details>

      <details class="st-lead-card">
        <summary>
          <span class="st-lead-card__leads">V1, V2</span>
          <span class="st-lead-card__title">중격 경색 Septal MI</span>
        </summary>
        <p>심실중격을 바라보는 lead입니다. V1-V2의 ST elevation은 중격 부위 손상을 시사합니다.</p>
        <p>LAD의 septal branch 영역과 연결해서 생각합니다. 새로 생긴 전도장애가 동반되는지도 확인합니다.</p>
      </details>

      <details class="st-lead-card">
        <summary>
          <span class="st-lead-card__leads">V3, V4</span>
          <span class="st-lead-card__title">전벽 경색 Anterior MI</span>
        </summary>
        <p>심장의 앞벽을 보는 lead입니다. V3-V4에서 ST elevation이 뚜렷하면 전벽 심근경색을 의심합니다.</p>
        <p>대개 LAD 폐색과 관련되어 손상 범위가 클 수 있습니다. 흉통, 혈압 저하, 심부전 징후를 빠르게 확인합니다.</p>
      </details>

      <details class="st-lead-card">
        <summary>
          <span class="st-lead-card__leads">I, aVL, V5, V6</span>
          <span class="st-lead-card__title">측벽 경색 Lateral MI</span>
        </summary>
        <p>심장의 왼쪽 옆벽을 보는 lead입니다. I, aVL은 높은 측벽, V5-V6는 낮은 측벽을 봅니다.</p>
        <p>LCx 또는 diagonal branch 영역과 관련될 수 있습니다. 다른 lead의 reciprocal change도 함께 확인합니다.</p>
      </details>

      <details class="st-lead-card">
        <summary>
          <span class="st-lead-card__leads">V1-V3 ST depression</span>
          <span class="st-lead-card__title">후벽 경색 Posterior MI</span>
        </summary>
        <p>후벽은 표준 12유도에서 직접 보이지 않아 V1-V3의 ST depression과 큰 R파로 숨어 나타날 수 있습니다.</p>
        <p>의심되면 posterior lead V7-V9를 추가로 붙여 확인합니다. 하벽 경색과 함께 동반될 수 있습니다.</p>
      </details>
    </div>

    <div class="note">
      간호사 팁: ST elevation을 보면 먼저 환자의 흉통, 활력징후, 의식 상태를 확인하고 즉시 의료진에게 보고합니다.
      이 화면은 교육용 참고 자료이며 실제 STEMI 판단은 병원 프로토콜과 전문가 판단을 따릅니다.
    </div>

    <section class="card hero result-guide">
      <div class="hero__kicker">ST/QT 관련 추가 소견</div>
      <div class="result-title">Long QT와 Brugada pattern</div>
      <div class="result-sub">사진을 클릭하면 크게 보고, 이름 영역을 클릭하면 설명이 펼쳐집니다.</div>
    </section>

    <div class="rhythm-grid" aria-label="ST 관련 추가 후보">
      ${stRelatedRhythms.map(renderRhythmCard).join("")}
    </div>
    ${renderImageModal()}
  `;
}

function renderQ2() {
  const state = loadAlgoState();
  const regLabel =
    state.regularity === "regular"
      ? "규칙적"
      : state.regularity === "irregular"
        ? "불규칙적"
        : "미선택";

  return `
    <section class="card hero">
      <div class="hero__kicker">2</div>
      <h2 class="hero__title" style="font-size: 18px; margin: 0;">심박수 범주는 어디에 해당하나요?</h2>
      <div class="hero__desc">
        현재 선택: <b>${regLabel}</b><br/>
        <b>빈맥은 100회 이상</b>, <b>정상은 60~100회</b>, <b>서맥은 60회 이하</b>로 나누어 선택합니다.
      </div>
    </section>

    <div class="choice-grid" role="group" aria-label="심박수 범주 선택">
      <div class="choice-card">
        <div class="choice-card__header">
          <div class="choice-card__title">빈맥</div>
          <span class="badge badge--accent">선택</span>
        </div>
        <div class="note">심박수 100회 이상 범주로 진행합니다.</div>
        <button class="primary" type="button" data-set-rate="tachy">선택</button>
      </div>

      <div class="choice-card">
        <div class="choice-card__header">
          <div class="choice-card__title">정상</div>
          <span class="badge">선택</span>
        </div>
        <div class="note">심박수 60~100회 범주로 진행합니다.</div>
        <button class="primary" type="button" data-set-rate="normal">선택</button>
      </div>

      <div class="choice-card">
        <div class="choice-card__header">
          <div class="choice-card__title">서맥</div>
          <span class="badge">선택</span>
        </div>
        <div class="note">심박수 60회 이하 범주로 진행합니다.</div>
        <button class="primary" type="button" data-set-rate="brady">선택</button>
      </div>
    </div>
  `;
}

function renderQ3() {
  const state = loadAlgoState();
  const hideWideQrs =
    state.regularity === "irregular" &&
    (state.rate === "normal" || state.rate === "brady");
  const regLabel =
    state.regularity === "regular"
      ? "규칙적"
      : state.regularity === "irregular"
        ? "불규칙적"
        : "미선택";
  const rateLabel =
    state.rate === "tachy"
      ? "빈맥"
      : state.rate === "normal"
        ? "정상"
        : state.rate === "brady"
          ? "서맥"
          : "미선택";

  return `
    <section class="card hero">
      <div class="hero__kicker">3</div>
      <h2 class="hero__title" style="font-size: 18px; margin: 0;">QRS는 wide인가요, narrow인가요?</h2>
      <div class="hero__desc">
        현재 선택: <b>${regLabel}</b> · <b>${rateLabel}</b><br/>
        다음은 QRS 폭만 선택합니다.
      </div>
    </section>

    <div class="choice-grid" role="group" aria-label="QRS 폭 선택">
      <div class="choice-card">
        <div class="choice-card__header">
          <div class="choice-card__title">Narrow QRS</div>
          <span class="badge badge--accent">선택</span>
        </div>
        <div class="note">좁은 QRS(대략 120ms 미만) 범주로 진행합니다.</div>
        <button class="primary" type="button" data-set-qrs="narrow">선택</button>
      </div>

      ${
        hideWideQrs
          ? ""
          : `
            <div class="choice-card">
              <div class="choice-card__header">
                <div class="choice-card__title">Wide QRS</div>
                <span class="badge">선택</span>
              </div>
              <div class="note">넓은 QRS(대략 120ms 이상) 범주로 진행합니다.</div>
              <button class="primary" type="button" data-set-qrs="wide">선택</button>
            </div>
          `
      }
    </div>
  `;
}

function renderSummary() {
  const state = loadAlgoState();
  const regLabel =
    state.regularity === "regular"
      ? "규칙적"
      : state.regularity === "irregular"
        ? "불규칙적"
        : "미선택";
  const rateLabel =
    state.rate === "tachy"
      ? "빈맥"
      : state.rate === "normal"
        ? "정상"
        : state.rate === "brady"
          ? "서맥"
          : "미선택";
  const qrsLabel =
    state.qrs === "narrow"
      ? "Narrow"
      : state.qrs === "wide"
        ? "Wide"
        : "미선택";

  const isNarrowRegularTachy =
    state.regularity === "regular" && state.rate === "tachy" && state.qrs === "narrow";
  const isNarrowIrregularTachy =
    state.regularity === "irregular" && state.rate === "tachy" && state.qrs === "narrow";
  const isWideRegularTachy =
    state.regularity === "regular" && state.rate === "tachy" && state.qrs === "wide";
  const isWideIrregularTachy =
    state.regularity === "irregular" && state.rate === "tachy" && state.qrs === "wide";
  const isNarrowRegularNormal =
    state.regularity === "regular" && state.rate === "normal" && state.qrs === "narrow";
  const isWideRegularNormal =
    state.regularity === "regular" && state.rate === "normal" && state.qrs === "wide";
  const isNarrowIrregularNormal =
    state.regularity === "irregular" && state.rate === "normal" && state.qrs === "narrow";
  const isNarrowRegularBrady =
    state.regularity === "regular" && state.rate === "brady" && state.qrs === "narrow";
  const isNarrowIrregularBrady =
    state.regularity === "irregular" && state.rate === "brady" && state.qrs === "narrow";
  const isWideRegularBrady =
    state.regularity === "regular" && state.rate === "brady" && state.qrs === "wide";

  return `
    <section class="card hero">
      <div class="hero__kicker">여기까지 완료</div>
      <div class="result-title">선택 요약</div>
      <div class="result-sub">
        1) 규칙성: <b>${regLabel}</b><br/>
        2) 심박수 범주: <b>${rateLabel}</b><br/>
        3) QRS 폭: <b>${qrsLabel}</b>
      </div>
    </section>

    ${
      isNarrowRegularTachy
        ? renderNarrowRegularTachyResults()
        : isNarrowIrregularTachy
          ? renderNarrowIrregularTachyResults()
        : isWideRegularTachy
          ? renderWideRegularTachyResults()
          : isWideIrregularTachy
            ? renderWideIrregularTachyResults()
          : isNarrowRegularNormal
            ? renderNarrowRegularNormalResults()
            : isWideRegularNormal
              ? renderWideRegularNormalResults()
            : isNarrowIrregularNormal
              ? renderNarrowIrregularNormalResults()
          : isNarrowRegularBrady
            ? renderNarrowRegularBradyResults()
            : isNarrowIrregularBrady
              ? renderNarrowIrregularBradyResults()
            : isWideRegularBrady
              ? renderWideRegularBradyResults()
        : renderUnmappedResult()
    }
  `;
}

function renderNarrowRegularTachyResults() {
  return `
    <section class="card hero result-guide">
      <div class="hero__kicker">후보 리듬</div>
      <div class="result-title">규칙적 빈맥 + Narrow QRS에서 볼 수 있는 리듬</div>
      <div class="result-sub">사진을 클릭하면 크게 보고, 이름 영역을 클릭하면 설명이 펼쳐집니다.</div>
    </section>

    <div class="rhythm-grid" aria-label="규칙적 narrow QRS 빈맥 후보">
      ${narrowRegularTachyRhythms.map(renderRhythmCard).join("")}
    </div>
    ${renderImageModal()}
  `;
}

function renderNarrowIrregularTachyResults() {
  return `
    <section class="card hero result-guide">
      <div class="hero__kicker">후보 리듬</div>
      <div class="result-title">불규칙 빈맥 + Narrow QRS에서 볼 수 있는 리듬</div>
      <div class="result-sub">사진을 클릭하면 크게 보고, 이름 영역을 클릭하면 설명이 펼쳐집니다.</div>
    </section>

    <div class="rhythm-grid" aria-label="불규칙 tachycardia narrow QRS 후보">
      ${narrowIrregularTachyRhythms.map(renderRhythmCard).join("")}
    </div>
    ${renderImageModal()}
  `;
}

function renderWideRegularTachyResults() {
  return `
    <section class="card hero result-guide">
      <div class="hero__kicker">후보 리듬</div>
      <div class="result-title">규칙적 빈맥 + Wide QRS에서 가장 먼저 생각할 리듬</div>
      <div class="result-sub">사진을 클릭하면 크게 보고, 이름 영역을 클릭하면 설명이 펼쳐집니다.</div>
    </section>

    <div class="rhythm-grid" aria-label="규칙적 wide QRS 빈맥 후보">
      ${wideRegularTachyRhythms.map(renderRhythmCard).join("")}
    </div>
    ${renderImageModal()}
  `;
}

function renderWideIrregularTachyResults() {
  return `
    <section class="card hero result-guide">
      <div class="hero__kicker">후보 리듬</div>
      <div class="result-title">불규칙 빈맥 + Wide QRS에서 볼 수 있는 리듬</div>
      <div class="result-sub">사진을 클릭하면 크게 보고, 이름 영역을 클릭하면 설명이 펼쳐집니다.</div>
    </section>

    <div class="rhythm-grid" aria-label="불규칙 tachycardia wide QRS 후보">
      ${wideIrregularTachyRhythms.map(renderRhythmCard).join("")}
    </div>
    ${renderImageModal()}
  `;
}

function renderNarrowRegularNormalResults() {
  return `
    <section class="card hero result-guide">
      <div class="hero__kicker">후보 리듬</div>
      <div class="result-title">규칙적 정상 심박수 + Narrow QRS에서 볼 수 있는 리듬</div>
      <div class="result-sub">사진을 클릭하면 크게 보고, 이름 영역을 클릭하면 설명이 펼쳐집니다.</div>
    </section>

    <div class="rhythm-grid" aria-label="규칙적 normal rate narrow QRS 후보">
      ${narrowRegularNormalRhythms.map(renderRhythmCard).join("")}
    </div>
    ${renderImageModal()}
  `;
}

function renderWideRegularNormalResults() {
  return `
    <section class="card hero result-guide">
      <div class="hero__kicker">후보 리듬</div>
      <div class="result-title">규칙적 정상 심박수 + Wide QRS에서 볼 수 있는 리듬</div>
      <div class="result-sub">사진을 클릭하면 크게 보고, 이름 영역을 클릭하면 설명이 펼쳐집니다.</div>
    </section>

    <div class="rhythm-grid" aria-label="규칙적 normal rate wide QRS 후보">
      ${wideRegularNormalRhythms.map(renderRhythmCard).join("")}
    </div>
    ${renderImageModal()}
  `;
}

function renderNarrowIrregularNormalResults() {
  return `
    <section class="card hero result-guide">
      <div class="hero__kicker">후보 리듬</div>
      <div class="result-title">불규칙 정상 심박수 + Narrow QRS에서 볼 수 있는 리듬</div>
      <div class="result-sub">사진을 클릭하면 크게 보고, 이름 영역을 클릭하면 설명이 펼쳐집니다.</div>
    </section>

    <div class="rhythm-grid" aria-label="불규칙 normal rate narrow QRS 후보">
      ${narrowIrregularNormalRhythms.map(renderRhythmCard).join("")}
    </div>
    ${renderImageModal()}
  `;
}

function renderNarrowRegularBradyResults() {
  return `
    <section class="card hero result-guide">
      <div class="hero__kicker">후보 리듬</div>
      <div class="result-title">규칙적 서맥 + Narrow QRS에서 볼 수 있는 리듬</div>
      <div class="result-sub">사진을 클릭하면 크게 보고, 이름 영역을 클릭하면 설명이 펼쳐집니다.</div>
    </section>

    <div class="rhythm-grid" aria-label="규칙적 narrow QRS 서맥 후보">
      ${narrowRegularBradyRhythms.map(renderRhythmCard).join("")}
    </div>
    ${renderImageModal()}
  `;
}

function renderNarrowIrregularBradyResults() {
  return `
    <section class="card hero result-guide">
      <div class="hero__kicker">후보 리듬</div>
      <div class="result-title">불규칙 서맥 + Narrow QRS에서 볼 수 있는 리듬</div>
      <div class="result-sub">사진을 클릭하면 크게 보고, 이름 영역을 클릭하면 설명이 펼쳐집니다.</div>
    </section>

    <div class="rhythm-grid" aria-label="불규칙 bradycardia narrow QRS 후보">
      ${narrowIrregularBradyRhythms.map(renderRhythmCard).join("")}
    </div>
    ${renderImageModal()}
  `;
}

function renderWideRegularBradyResults() {
  return `
    <section class="card hero result-guide">
      <div class="hero__kicker">후보 리듬</div>
      <div class="result-title">규칙적 서맥 + Wide QRS에서 볼 수 있는 리듬</div>
      <div class="result-sub">사진을 클릭하면 크게 보고, 이름 영역을 클릭하면 설명이 펼쳐집니다.</div>
    </section>

    <div class="rhythm-grid" aria-label="규칙적 wide QRS 서맥 후보">
      ${wideRegularBradyRhythms.map(renderRhythmCard).join("")}
    </div>
    ${renderImageModal()}
  `;
}

function renderPacemakerResults() {
  return `
    <section class="card hero result-guide">
      <div class="hero__kicker">Pacemaker 관련</div>
      <div class="result-title">Pacemaker 리듬과 기능 이상</div>
      <div class="result-sub">사진을 클릭하면 크게 보고, 이름 영역을 클릭하면 설명이 펼쳐집니다.</div>
    </section>

    <div class="rhythm-grid" aria-label="Pacemaker 관련 후보">
      ${pacemakerRhythms.map(renderRhythmCard).join("")}
    </div>
    ${renderImageModal()}
  `;
}

function renderRhythmCard(rhythm) {
  return `
    <details class="rhythm-card">
      <summary class="rhythm-card__summary">
        ${renderRhythmImage(rhythm)}
        <span class="rhythm-card__name">${rhythm.name}</span>
        <span class="rhythm-card__english">${rhythm.englishName}</span>
        <span class="rhythm-card__hint">클릭해서 설명 보기</span>
      </summary>
      <div class="rhythm-card__detail">
        ${rhythm.description.map((line) => `<p>${line}</p>`).join("")}
        ${rhythm.subtypes ? renderRhythmSubtypes(rhythm.subtypes) : ""}
      </div>
    </details>
  `;
}

function renderRhythmImage(rhythm) {
  return `
    <span class="rhythm-card__image-wrap">
      <img
        class="rhythm-card__image"
        src="${rhythm.image}"
        alt="${rhythm.alt}"
        role="button"
        tabindex="0"
        data-zoom-src="${rhythm.image}"
        data-zoom-title="${rhythm.name} (${rhythm.englishName})"
      />
    </span>
  `;
}

function renderRhythmSubtypes(subtypes) {
  return `
    <div class="rhythm-subtypes">
      <div class="rhythm-subtypes__title">PAC의 종류</div>
      <div class="rhythm-subtypes__grid">
        ${subtypes
          .map(
            (subtype) => `
              <article class="rhythm-subtype">
                <img
                  class="rhythm-subtype__image"
                  src="${subtype.image}"
                  alt="${subtype.alt}"
                  role="button"
                  tabindex="0"
                  data-zoom-src="${subtype.image}"
                  data-zoom-title="${subtype.name}"
                />
                <div class="rhythm-subtype__name">${subtype.name}</div>
                ${subtype.description.map((line) => `<p>${line}</p>`).join("")}
              </article>
            `
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderImageModal() {
  return `
    <div class="image-modal" data-image-modal hidden>
      <div class="image-modal__dialog" role="dialog" aria-modal="true" aria-labelledby="image-modal-title">
        <div class="image-modal__header">
          <div class="image-modal__title" id="image-modal-title" data-modal-title>심전도 사진</div>
          <button class="image-modal__close" type="button" data-modal-close aria-label="확대 사진 닫기">닫기</button>
        </div>
        <img class="image-modal__image" data-modal-image alt="" />
      </div>
    </div>
  `;
}

function renderUnmappedResult() {
  return `
    <div style="height: 12px"></div>
    <div class="choice-grid">
      <div class="choice-card">
        <div class="choice-card__header">
          <div class="choice-card__title">아직 연결되지 않은 경로</div>
          <span class="badge">준비중</span>
        </div>
        <div class="note">
          현재는 <b>규칙적 + 빈맥 + Narrow QRS</b>, <b>불규칙 + 빈맥 + Narrow QRS</b>,
          <b>규칙적 + 빈맥 + Wide QRS</b>, <b>불규칙 + 빈맥 + Wide QRS</b>,
          <b>규칙적 + 정상 + Narrow QRS</b>, <b>규칙적 + 정상 + Wide QRS</b>,
          <b>불규칙 + 정상 + Narrow QRS</b>,
          <b>규칙적 + 서맥 + Narrow QRS</b>, <b>불규칙 + 서맥 + Narrow QRS</b>,
          <b>규칙적 + 서맥 + Wide QRS</b> 경로를 먼저 연결했습니다.
        </div>
        <button class="secondary" type="button" data-action="algo-reset">다시 시작</button>
      </div>
    </div>
  `;
}

function renderAiScreen() {
  return `
    <div class="toolbar">
      <button class="link" type="button" data-nav="#/menu">← 메뉴로</button>
    </div>

    <div class="screen-title">카메라로 찾기</div>
    <section class="card hero">
      <div class="hero__kicker">AI 판독 앱 연결</div>
      <h2 class="hero__title" style="font-size: 18px; margin: 0;">Streamlit 카메라 판독 앱을 실행해 주세요</h2>
      <div class="hero__desc">
        카메라 AI 판독은 Python/Streamlit 서버에서 실행됩니다. 먼저 터미널에서 아래 명령을 실행한 뒤 버튼을 눌러 주세요.<br/><br/>
        <b>.\ecg_cnn_env\Scripts\activate; streamlit run streamlit_ecg_decision_app.py</b><br/><br/>
        서버가 켜져 있지 않으면 버튼을 눌러도 카메라 화면이 열리지 않습니다.
      </div>
    </section>
    <div class="note">
      카카오톡으로 공유하려면 이 PC의 파일 경로가 아니라 <b>https://...</b> 웹주소가 필요합니다.
      임시 테스트는 ngrok 같은 터널을 사용하거나, 최종 공유는 Streamlit Community Cloud/Render 등에 배포해야 합니다.
    </div>
    <button class="primary" type="button" data-open-camera-app>카메라 AI 판독 앱 열기</button>
  `;
}

function bindAiActions() {
  document.querySelectorAll("[data-open-camera-app]").forEach((btn) => {
    btn.addEventListener("click", () => {
      window.open(STREAMLIT_CAMERA_URL, "_blank", "noopener,noreferrer");
    });
  });
}

// PWA 서비스워커(선택)
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./service-worker.js").catch(() => {
      // 실패해도 앱은 동작해야 하므로 조용히 무시
    });
  });
}

window.addEventListener("hashchange", render);
window.addEventListener("DOMContentLoaded", () => {
  if (!location.hash) location.hash = "#/menu";
  render();
});

