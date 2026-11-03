// AmpT 펌웨어 상수 — 숫자는 모두 여기서만 바꾼다.
// TODO 표시는 아직 실측·확인 전인 값.
#pragma once

// ---------- 핀 (docs/pins.md, 임시) ----------
const int PIN_Z_STEP = 2;
const int PIN_Z_DIR = 3;
const int PIN_X_STEP = 4;
const int PIN_X_DIR = 5;
const int PIN_DRV_EN = 6;  // LOW = 드라이버 켜짐
const int PIN_ROT_IN1 = 7;
const int PIN_ROT_IN2 = 8;
const int PIN_ROT_IN3 = 9;
const int PIN_ROT_IN4 = 10;
const int PIN_CLAMP_A = 11;
const int PIN_CLAMP_B = 12;
const int PIN_HX_DOUT = 13;
const int PIN_HX_SCK = 14;
const int PIN_LIM_Z = 15;  // 눌리면 LOW (INPUT_PULLUP)
const int PIN_LIM_X = 16;
const int PIN_VAC = 17;
const int PIN_LIGHT = 18;
const int PIN_COVER = 19;  // 닫힘 = LOW, 열림 = HIGH
const int PIN_ESTOP = 20;  // 정상 = LOW, 눌림 = HIGH
const int PIN_START = 21;

// ---------- 리드스크류 축 (Z · X 공통, NEMA17 + TMR8 리드 1.5) ----------
const float MICROSTEPS = 16;
const float STEPS_PER_MM = 200.0 * MICROSTEPS / 1.5;  // 2133.3

// 아래 기구 값 4개는 실측 전 임시값. CAD v2.5.22(11/3) 참고값을 옆에 적어 둠 — 출력 · 조립한 실물은 다를 수 있어 실측으로 정한다
const float Z_TRAVEL_MM = 60.0;      // TODO 실측. CAD: 원점 아래 약 44.5에서 Z 너트가 커플러에 닿음 → 40 이하 (1 mL에 필요한 건 약 37.5)
const float Z_TOP_NOTCH_MM = 62.0;   // TODO 실측. Z가 맨 위일 때 푸셔가 미는 노치 높이. CAD: 62~63 (푸셔 높이 = 노치 + 15)
const float Z_SPEED_MM_S = 10.0;
const float Z_ACCEL_MM_S2 = 40.0;
const float Z_HOME_SPEED_MM_S = 5.0;

const float X_SPEED_MM_S = 10.0;     // 빈 이동
const float X_ACCEL_MM_S2 = 40.0;
const float X_HOME_SPEED_MM_S = 3.0;
const float X_APPROACH_MM = 0.0;     // TODO 실측. 원점에서 머리 닿기 직전까지 빠르게 갈 거리. CAD: 닿는 거리 d − 1.5 ≈ 8.5 (d = 10.1 5 mL · 10.4 1 mL)
// 11/1 5 → 2 mm/s: 파편 시험 조건(B · C = 2 mm/s)과 맞추고, 로드셀이 10 Hz인 동안
// 최대 힘 → 판정 사이에 더 미는 거리를 줄인다 (0.29초 × 5 mm/s = 1.4 mm → × 2 mm/s = 0.6 mm)
const float PUSH_SPEED_MM_S = 2.0;
#ifdef DESK_TEST
// 책상 시험: 로드셀을 손으로 눌렀다 뗄 시간 (30 mm ÷ 2 mm/s = 15초) — 기구에 달면 이 플래그 없이 올린다
const float PUSH_LIMIT_MM = 30.0;
#else
const float PUSH_LIMIT_MM = 6.0;     // TODO 실측. 위치 제한 (두 겹 보호의 둘째). CAD: d + 2.8 ≈ 12.9, 최대 13.2 — 6이면 유리에 닿지 않는다
#endif

// ---------- 파단 판정 ----------
const float STOP_FORCE_N = 43.0;     // 정지값 = 1.2 × 기계 파단력 36 N
const float BREAK_MIN_PEAK_N = 5.0;  // TODO 파단 시험으로 정함 — 이 힘 아래 흔들림은 무시
const float BREAK_DROP_RATIO = 0.5;  // TODO 피크의 50 % 아래로 떨어지면 파단
const int BREAK_CONFIRM_SAMPLES = 2; // 80 Hz에서 2샘플 = 25 ms (개조 전 10 Hz면 200 ms)

// ---------- 로드셀 (HX711, RATE High = 80 Hz — 산 보드는 개조 전 10 Hz 실측) ----------
// 실측 11/1: 예비 HX711 + 예비 로드셀로 교체 후 512 g을 자유단에 매달아 bench `cal` (+ = 자유단 아래로).
// (10/31 값 45061.9는 고장 의심 보드 · 로드셀 기준.) 보드를 바꾸거나 기구에 달면 다시 cal
const float LOADCELL_COUNTS_PER_N = 49059.7;
const int LOADCELL_TARE_SAMPLES = 5;
// HX711 끝값은 ±8388608. 값이 이 근처에 붙으면 로드셀 선(E± · A±)이 빠졌거나 보드 고장이라
// 힘을 못 읽는다 → PUSH를 하지 않고 ERR LOADCELL (11/1 실제로 겪음: 힘이 0.00 N으로만 찍혔다).
// 정상이면 영점(지금 약 −60만)에 43 N(약 210만)을 더해도 300만 아래라 여기까지 오지 않는다
const long LOADCELL_SATURATED_COUNTS = 8300000;

// ---------- 회전 (28BYJ-48 + ULN2003, 하프스텝) ----------
const float ROT_STEPS_PER_REV = 4096.0;  // 실측 10/30: ROT 3600 뒤 깃발이 제자리 (4076이면 +18°)
const float ROT_SPEED_STEPS_S = 800.0;
const float ROT_ACCEL_STEPS_S2 = 1600.0;

// ---------- 클램프 (N20, 시간으로 조임) ----------
// 11/1 책상 (기구 없이): N20 → TC1508A MOTOR-A, 6.0 V. CLAMP 1 = 축을 축 쪽에서 볼 때 시계 방향.
// 이게 닫히는 방향인지는 기구에 달고 확인 — 반대면 MOTOR-A의 두 선을 서로 바꾼다 (코드는 그대로)
// 11/3 200 → 128: 6 V × 128/255 ≈ 3 V로 약하게 시작. N20을 끝까지 조이면 190~310 N(계산, CAD v2.5.9)이라 앰플 · 출력 조가 상할 수 있다.
// 앰플이 미끄러지면 올린다 (CAD v2.5.22 README · 팀 전장 가이드 11/2와 같은 권장)
const int CLAMP_PWM = 128;             // 0~255, TODO N20 정지 토크 실측 후
const unsigned long CLAMP_CLOSE_MS = 1500;  // TODO
const unsigned long CLAMP_OPEN_MS = 1500;   // TODO

// ---------- 안전 ----------
// 책상 시험 때 덮개·비상정지 스위치가 없으면 늘 '열림'으로 읽혀 멈춘다 → 잠시 무시.
// TODO 스위치를 달면 반드시 false
const bool IGNORE_SAFETY_INPUTS = true;

// ---------- 통신 ----------
const unsigned long SERIAL_BAUD = 115200;
