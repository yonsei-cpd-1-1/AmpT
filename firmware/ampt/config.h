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
// 방향: 11/3 기구 bench 시험에서 X가 반대로 돎 (x 1 = 뒤, x -1 = 앞) → 코드로 뒤집음 (선은 그대로).
// 맞는 방향: Z + = 아래 · X + = 앰플 쪽. bench.ino에도 같은 값이 있다 (바꾸면 둘 다)
const bool Z_DIR_INVERT = false;
const bool X_DIR_INVERT = true;
const float MICROSTEPS = 16;
const float STEPS_PER_MM = 200.0 * MICROSTEPS / 1.5;  // 2133.3

// 기구 값: 11/3 팀원 실측(자로, X · Z 원점 상태)으로 3개를 정함 — docs/testlog.md 11/3. Z_TOP_NOTCH는 클램프 조 높이를 잰 뒤
// 11/3 밤 기구 시험: LIFT 22 (원점에서 40 mm)에서 아래에 부딪힘 → 5 mm씩 내려 본 뒤 박도울 "LIFT 37까지만" = 25 mm.
// 이 값이면 1 mL 노치 높이(원점에서 약 26~32 mm 필요)에는 못 내려간다 (설계/03 Q-78)
const float Z_TRAVEL_MM = 25.0;      // 처음 값 40 — 팀원 실측 11/3: 원점에서 44 mm 내려가면 푸셔쪽 하우징이 덱에 닿음 → 40 (CAD는 44.5에서 Z 너트 ↔ 커플러). 필요한 건 약 30
// 11/3 밤 박도울: 원점 스위치 높이까지는 HOME 때만 올라가고, 그 뒤로는 이만큼 아래가 맨 위.
// HOME = 스위치에 닿아 0을 잡고 → 이 높이로 내려와서 → X 원점. ZTOP도 여기까지. 좌표(0 = 스위치)는 그대로
const float Z_PARK_MM = 5.0;
const float Z_TOP_NOTCH_MM = 62.0;   // TODO 클램프 조 높이를 재고 정함 = 원점에서 조 가운데 높이(앰플 바닥 기준) + 8. 푸셔 기준(노치 + 15)이면 70.5 − 15 = 55.5. 62면 푸셔가 노치에 너무 가까움
const float Z_SPEED_MM_S = 10.0;
const float Z_ACCEL_MM_S2 = 40.0;
const float Z_HOME_SPEED_MM_S = 5.0;

const float X_SPEED_MM_S = 10.0;     // 빈 이동
const float X_ACCEL_MM_S2 = 40.0;
const float X_HOME_SPEED_MM_S = 3.0;
// 11/3 밤 박도울: X도 원점 스위치까지는 HOME 때만, 그 뒤로는 이만큼 앞이 맨 뒤 (PUSH 후퇴도 여기까지).
// 좌표(0 = 스위치)는 그대로 → 앰플까지 d 8.9에서 남는 틈 3.9 mm. X_APPROACH_MM보다 작아야 한다
constexpr float X_PARK_MM = 5.0;
// ★ X 마지노선 (11/3 밤 박도울, bench로 조금씩 밀어 정함): 원점 스위치에서 16.25 mm.
//   5 mm 자리에서 x 7.5바퀴 (1 + 1 + 1 + 0.5×4 + 0.3 + 0.2 + 0.2 + 0.3 + 0.3 + 0.5 + 0.5 + 0.2) × 1.5 mm = 11.25 mm.
//   이보다 앞은 MGN 블록이 레일을 벗어난다 → 어떤 빌드 · 명령으로도 넘지 않는다.
//   아래 static_assert로 PUSH_LIMIT · X_APPROACH가 이 값을 넘으면 컴파일이 안 되고, 펌웨어는 매 루프 위치를 봐서
//   넘으면 바로 비상정지(ERR XMAX)한다
constexpr float X_HARD_MAX_MM = 16.25;
constexpr float X_APPROACH_MM = 7.4;     // 실측 11/3: 원점에서 앰플 닿는 거리 d = 8.9 (5 mL) · 9.2 (1 · 2 mL) → 짧은 쪽 d − 1.5 (CAD는 d 10.1 · 10.4)
// 11/1 5 → 2 mm/s: 파편 시험 조건(B · C = 2 mm/s)과 맞추고, 로드셀이 10 Hz인 동안
// 최대 힘 → 판정 사이에 더 미는 거리를 줄인다 (0.29초 × 5 mm/s = 1.4 mm → × 2 mm/s = 0.6 mm)
const float PUSH_SPEED_MM_S = 2.0;
#ifdef DESK_TEST
// 책상 시험: 로드셀을 손으로 눌렀다 뗄 시간 (16 mm ÷ 2 mm/s = 8초) — 기구에 달면 이 플래그 없이 올린다
constexpr float PUSH_LIMIT_MM = 16.0;   // 11/3 30 → 16: 기구에서는 X 마지노선(X_HARD_MAX_MM) 16.25를 넘을 수 없다
#else
constexpr float PUSH_LIMIT_MM = 11.7;    // 위치 제한 (두 겹 보호의 둘째). 실측 11/3: d + 2.8 = 11.7 (5 mL) · 12.0 (1 · 2 mL) → 짧은 쪽. 원점에서 12.0을 넘으면 X 너트 플랜지 ↔ 푸셔쪽 조 (여유 0.77, 계산 — 11/3 밤 bench로 16.25까지 밀어 봄)
#endif
static_assert(X_PARK_MM < X_APPROACH_MM, "X_PARK_MM must be behind X_APPROACH_MM");
static_assert(X_APPROACH_MM < PUSH_LIMIT_MM, "X_APPROACH_MM must be behind PUSH_LIMIT_MM");
static_assert(PUSH_LIMIT_MM <= X_HARD_MAX_MM, "PUSH_LIMIT_MM beyond X_HARD_MAX_MM (rail end)");

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
// 닫히는 방향이 반대면 true (선 대신 코드로 바꿈 — X와 같은 방식). 11/4 기구에서 CJOG로 확인
const bool CLAMP_DIR_INVERT = false;
// CJOG <ms> [pwm]: 시험용 조금씩 움직이기 (+ 닫기 · − 열기). 한 번에 이 시간까지만
const unsigned long CLAMP_JOG_MAX_MS = 1000;
const int CLAMP_PWM = 128;             // 0~255, TODO N20 정지 토크 실측 후
const unsigned long CLAMP_CLOSE_MS = 1500;  // TODO
const unsigned long CLAMP_OPEN_MS = 1500;   // TODO

// ---------- 안전 ----------
// 책상 시험 때 덮개·비상정지 스위치가 없으면 늘 '열림'으로 읽혀 멈춘다 → 잠시 무시.
// TODO 스위치를 달면 반드시 false
const bool IGNORE_SAFETY_INPUTS = true;

// ---------- 통신 ----------
const unsigned long SERIAL_BAUD = 115200;
