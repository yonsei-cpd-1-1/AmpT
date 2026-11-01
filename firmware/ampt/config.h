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

const float Z_TRAVEL_MM = 60.0;      // TODO 윤정호 CAD로 확인 (Z 행정)
const float Z_TOP_NOTCH_MM = 62.0;   // TODO Z가 맨 위일 때 푸셔가 미는 노치 높이
const float Z_SPEED_MM_S = 10.0;
const float Z_ACCEL_MM_S2 = 40.0;
const float Z_HOME_SPEED_MM_S = 5.0;

const float X_SPEED_MM_S = 10.0;     // 빈 이동
const float X_ACCEL_MM_S2 = 40.0;
const float X_HOME_SPEED_MM_S = 3.0;
const float X_APPROACH_MM = 0.0;     // TODO 원점에서 머리 닿기 직전까지 빠르게 갈 거리
const float PUSH_SPEED_MM_S = 5.0;   // 운전 속도. 파편 시험 조건(2 mm/s)과 아직 다르다
#ifdef DESK_TEST
// 책상 시험: 로드셀을 손으로 눌렀다 뗄 시간 (6 mm면 1.2 초뿐) — 기구에 달면 이 플래그 없이 올린다
const float PUSH_LIMIT_MM = 30.0;
#else
const float PUSH_LIMIT_MM = 6.0;     // TODO 위치 제한 — 윤정호 확인 (두 겹 보호의 둘째)
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

// ---------- 회전 (28BYJ-48 + ULN2003, 하프스텝) ----------
const float ROT_STEPS_PER_REV = 4096.0;  // 실측 10/30: ROT 3600 뒤 깃발이 제자리 (4076이면 +18°)
const float ROT_SPEED_STEPS_S = 800.0;
const float ROT_ACCEL_STEPS_S2 = 1600.0;

// ---------- 클램프 (N20, 시간으로 조임) ----------
const int CLAMP_PWM = 200;             // 0~255, TODO N20 정지 토크 실측 후
const unsigned long CLAMP_CLOSE_MS = 1500;  // TODO
const unsigned long CLAMP_OPEN_MS = 1500;   // TODO

// ---------- 안전 ----------
// 책상 시험 때 덮개·비상정지 스위치가 없으면 늘 '열림'으로 읽혀 멈춘다 → 잠시 무시.
// TODO 스위치를 달면 반드시 false
const bool IGNORE_SAFETY_INPUTS = true;

// ---------- 통신 ----------
const unsigned long SERIAL_BAUD = 115200;
