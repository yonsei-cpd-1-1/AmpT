// AmpT Pico 2 펌웨어 — Pi가 보낸 한 줄 명령을 받아 모터·로드셀을 움직인다.
// 명령표: docs/protocol.md, 핀: docs/pins.md, 숫자: config.h
// 보드: Raspberry Pi Pico 2 (arduino-pico), 라이브러리: AccelStepper, HX711 (Rob Tillaart)

#include <AccelStepper.h>
#include <HX711.h>

#include "break_detector.h"
#include "config.h"

AccelStepper zAxis(AccelStepper::DRIVER, PIN_Z_STEP, PIN_Z_DIR);  // + = 아래
AccelStepper xAxis(AccelStepper::DRIVER, PIN_X_STEP, PIN_X_DIR);  // + = 앰플 쪽
// 28BYJ-48: AccelStepper 코일 순서는 IN1, IN3, IN2, IN4
AccelStepper rotAxis(AccelStepper::HALF4WIRE, PIN_ROT_IN1, PIN_ROT_IN3, PIN_ROT_IN2, PIN_ROT_IN4);
HX711 loadcell;
BreakDetector detector(STOP_FORCE_N, BREAK_MIN_PEAK_N, BREAK_DROP_RATIO, BREAK_CONFIRM_SAMPLES);

// 한 번에 하나만 도는 일 (ROT는 따로 — 다른 축과 동시에 돈다)
enum Task { IDLE, HOME_Z, HOME_Z_BACK, HOME_X, HOME_X_BACK, MOVE_Z, PUSH_APPROACH, PUSHING, RETREAT, CLAMPING };
Task task = IDLE;

bool homed = false;
bool stopped = false;
bool rotBusy = false;
const char* doneReply = "";  // 지금 일이 끝나면 보낼 줄
char resultReply[32];        // PUSH 결과 (후퇴가 끝난 뒤 보냄)

long tareCounts = 0;
unsigned long pushStartMs = 0;
unsigned long lastSampleMs = 0;
unsigned long clampStartMs = 0;
unsigned long clampDurationMs = 0;
bool startWasPressed = false;

String lineBuf;

long mmToSteps(float mm) { return lround(mm * STEPS_PER_MM); }
float stepsToMm(long steps) { return steps / STEPS_PER_MM; }

// 움직이던 상태를 버리고 지금 위치에서 멈춘다 (위치 값은 유지)
void haltAxis(AccelStepper& axis) { axis.setCurrentPosition(axis.currentPosition()); }

void clampMotor(int a, int b) {
  analogWrite(PIN_CLAMP_A, a);
  analogWrite(PIN_CLAMP_B, b);
}

// ---------- 안전 ----------

bool estopPressed() { return !IGNORE_SAFETY_INPUTS && digitalRead(PIN_ESTOP) == HIGH; }
bool coverOpen() { return !IGNORE_SAFETY_INPUTS && digitalRead(PIN_COVER) == HIGH; }

void emergencyStop(const char* reason) {
  digitalWrite(PIN_DRV_EN, HIGH);
  rotAxis.disableOutputs();
  clampMotor(0, 0);
  digitalWrite(PIN_VAC, LOW);
  haltAxis(zAxis);
  haltAxis(xAxis);
  haltAxis(rotAxis);
  task = IDLE;
  rotBusy = false;
  stopped = true;
  Serial.println(reason);
}

void checkSafety() {
  if (stopped) return;
  if (estopPressed()) emergencyStop("ESTOP");
  else if (coverOpen()) emergencyStop("COVER OPEN");
}

// ---------- 명령 ----------

void startMoveZ(float zMm, const char* reply) {
  zAxis.moveTo(mmToSteps(zMm));
  doneReply = reply;
  task = MOVE_Z;
}

// 값이 HX711 끝값에 붙음 = 로드셀 선이 빠졌거나 보드 고장 (config.h LOADCELL_SATURATED_COUNTS)
bool loadcellSaturated(long counts) { return labs(counts) >= LOADCELL_SATURATED_COUNTS; }

void startPush() {
  if (!loadcell.wait_ready_timeout(500)) {
    Serial.println("ERR LOADCELL");
    return;
  }
  long tare = lround(loadcell.read_average(LOADCELL_TARE_SAMPLES));
  if (loadcellSaturated(tare)) {  // 이대로 밀면 힘이 늘 0으로 읽혀 43 N 정지가 안 걸린다
    Serial.println("ERR LOADCELL");
    return;
  }
  tareCounts = tare;
  detector.reset();
  xAxis.moveTo(mmToSteps(X_APPROACH_MM));
  task = PUSH_APPROACH;
}

// close = 닫는 쪽. CLAMP_DIR_INVERT면 두 선을 바꾼 것과 같다
void driveClamp(bool close, int pwm) {
  if (close != CLAMP_DIR_INVERT) clampMotor(pwm, 0);
  else clampMotor(0, pwm);
}

void startClamp(bool close) {
  driveClamp(close, CLAMP_PWM);
  clampStartMs = millis();
  clampDurationMs = close ? CLAMP_CLOSE_MS : CLAMP_OPEN_MS;
  doneReply = "OK CLAMP";
  task = CLAMPING;
}

// 시험용: CJOG <ms> [pwm] — + 닫기 · − 열기, 0 = 누적 시간 지우기. 누적(닫은 ms − 연 ms)을 알려 줘서
// 다 열린 자리 → 앰플에 닿는 자리까지의 시간을 CLAMP_CLOSE_MS로 옮겨 적는다 (11/4)
long clampJogTotalMs = 0;
char clampJogReply[48];

void startClampJog(String arg) {
  arg.trim();
  int sp = arg.indexOf(' ');
  long ms = (sp < 0 ? arg : arg.substring(0, sp)).toInt();
  int pwm = sp < 0 ? CLAMP_PWM : arg.substring(sp + 1).toInt();
  if (ms == 0) {
    clampJogTotalMs = 0;
    Serial.println("OK CJOG total 0 ms");
    return;
  }
  if ((unsigned long)labs(ms) > CLAMP_JOG_MAX_MS || pwm < 1 || pwm > 255) {
    Serial.printf("ERR RANGE (1~%lu ms, pwm 1~255)\n", CLAMP_JOG_MAX_MS);
    return;
  }
  driveClamp(ms > 0, pwm);
  clampStartMs = millis();
  clampDurationMs = labs(ms);
  clampJogTotalMs += ms;
  snprintf(clampJogReply, sizeof(clampJogReply), "OK CJOG %+ld ms pwm %d, total %+ld ms", ms, pwm, clampJogTotalMs);
  doneReply = clampJogReply;
  task = CLAMPING;
}

void handleCommand(String line) {
  line.trim();
  if (line.length() == 0) return;
  int sp = line.indexOf(' ');
  String cmd = sp < 0 ? line : line.substring(0, sp);
  String arg = sp < 0 ? "" : line.substring(sp + 1);
  cmd.toUpperCase();

  if (cmd == "STATUS") {
    Serial.println(stopped ? "STATUS STOPPED" : (task == IDLE && !rotBusy) ? "STATUS IDLE" : "STATUS BUSY");
    return;
  }
  if (cmd == "RESET") {
    if (estopPressed() || coverOpen()) {
      Serial.println("ERR STOPPED");
      return;
    }
    stopped = false;
    homed = false;  // 멈춘 사이 손으로 움직였을 수 있음 → 다시 HOME
    digitalWrite(PIN_DRV_EN, LOW);
    rotAxis.enableOutputs();
    Serial.println("OK RESET");
    return;
  }
  if (stopped) {
    Serial.println("ERR STOPPED");
    return;
  }

  if (cmd == "ROT") {
    if (rotBusy) {
      Serial.println("ERR BUSY");
      return;
    }
    rotAxis.move(lround(arg.toFloat() / 360.0 * ROT_STEPS_PER_REV));
    rotBusy = true;
    return;
  }
  if (cmd == "VAC") {
    digitalWrite(PIN_VAC, arg.toInt() ? HIGH : LOW);
    Serial.println("OK VAC");
    return;
  }
  if (cmd == "INDEX") {
    Serial.println("ERR NOTSUPPORTED");
    return;
  }

  bool known = cmd == "HOME" || cmd == "ZTOP" || cmd == "LIFT" || cmd == "CLAMP" || cmd == "CJOG" || cmd == "PUSH";
  if (!known) {
    Serial.println("ERR UNKNOWN " + cmd);
    return;
  }
  if (task != IDLE) {
    Serial.println("ERR BUSY");
    return;
  }

  if (cmd == "HOME") {
    // 찾는 거리 한도를 지금 자리부터 센다 — 안 그러면 한 번 실패한 뒤엔 다음 HOME이 바로 ERR HOME
    // (setCurrentPosition은 속도를 0으로 만들므로 setSpeed보다 먼저)
    homed = false;
    zAxis.setCurrentPosition(0);
    xAxis.setCurrentPosition(0);
    zAxis.setSpeed(-Z_HOME_SPEED_MM_S * STEPS_PER_MM);
    task = HOME_Z;
  } else if (cmd == "CLAMP") {
    startClamp(arg.toInt() == 1);
  } else if (cmd == "CJOG") {
    startClampJog(arg);
  } else if (!homed) {
    Serial.println("ERR NOTHOMED");
  } else if (cmd == "ZTOP") {
    startMoveZ(Z_PARK_MM, "OK ZTOP");  // 스위치보다 Z_PARK_MM 아래 (config.h)
  } else if (cmd == "LIFT") {
    float zMm = Z_TOP_NOTCH_MM - arg.toFloat();
    if (zMm < Z_PARK_MM || zMm > Z_TRAVEL_MM) Serial.println("ERR RANGE");
    else startMoveZ(zMm, "OK LIFT");
  } else if (cmd == "PUSH") {
    startPush();
  }
}

void readSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {  // 터미널마다 Enter가 CR · LF · CRLF로 다름 — 빈 줄은 무시됨
      handleCommand(lineBuf);
      lineBuf = "";
    } else if (c == '\b' || c == 0x7F) {  // 백스페이스 (맥은 0x7F, 윈도우는 0x08) → 한 글자 지움
      if (lineBuf.length() > 0) lineBuf.remove(lineBuf.length() - 1);
    } else if (c >= 0x20 && c < 0x7F && lineBuf.length() < 64) {
      // 보이는 영문 · 숫자 · 기호만 받는다. Ctrl+C 같은 제어 문자나 한글 입력이 섞여
      // 다음 명령이 ERR UNKNOWN이 되던 것을 막는다
      lineBuf += c;
    }
  }
}

// ---------- 매 루프 진행 ----------

void finishPush(const char* result) {
  strncpy(resultReply, result, sizeof(resultReply) - 1);
  haltAxis(xAxis);
  xAxis.moveTo(mmToSteps(X_PARK_MM));  // 스위치보다 X_PARK_MM 앞까지만 (config.h)
  task = RETREAT;
}

void runPush() {
  // 위치 제한은 로드셀 샘플(10 Hz)을 기다리지 않고 매 루프, 한 스텝 내딛기 전에 본다
  // (전에는 샘플이 올 때만 봐서 0.2~0.4 mm 더 나갈 수 있었다)
  if (xAxis.currentPosition() >= mmToSteps(PUSH_LIMIT_MM)) {
    finishPush("NOBREAK LIMIT");
    return;
  }
  xAxis.runSpeed();
  if (loadcell.is_ready()) {
    lastSampleMs = millis();
    long raw = lround(loadcell.read());
    if (loadcellSaturated(raw)) {  // 밀던 중에 선이 빠짐 → 멈추고 후퇴
      finishPush("ERR LOADCELL");
      return;
    }
    float forceN = (raw - tareCounts) / LOADCELL_COUNTS_PER_N;
    float xMm = stepsToMm(xAxis.currentPosition());
    Serial.printf("FORCE %lu,%.2f,%.3f\n", millis() - pushStartMs, forceN, xMm);

    BreakDetector::Result r = detector.update(forceN);
    if (r == BreakDetector::BROKE) {
      char buf[32];
      snprintf(buf, sizeof(buf), "BROKE %.1f", detector.peak());
      finishPush(buf);
    } else if (r == BreakDetector::NOBREAK) {
      finishPush("NOBREAK");
    }
  } else if (millis() - lastSampleMs > 200) {
    finishPush("ERR LOADCELL");
  }
}

void runTask() {
  switch (task) {
    case IDLE:
      break;
    case HOME_Z:
      zAxis.runSpeed();
      if (digitalRead(PIN_LIM_Z) == LOW) {
        zAxis.setCurrentPosition(0);
        zAxis.moveTo(mmToSteps(Z_PARK_MM));  // 스위치에서 바로 내려온다 (11/3 박도울)
        task = HOME_Z_BACK;
      } else if (zAxis.currentPosition() < -mmToSteps(Z_TRAVEL_MM + 10)) {
        haltAxis(zAxis);
        task = IDLE;
        Serial.println("ERR HOME");
      }
      break;
    case HOME_Z_BACK:
      if (!zAxis.run()) {
        xAxis.setSpeed(-X_HOME_SPEED_MM_S * STEPS_PER_MM);
        task = HOME_X;
      }
      break;
    case HOME_X:
      xAxis.runSpeed();
      if (digitalRead(PIN_LIM_X) == LOW) {
        xAxis.setCurrentPosition(0);
        xAxis.moveTo(mmToSteps(X_PARK_MM));  // 스위치에서 바로 앞으로 나온다 (11/3 박도울)
        task = HOME_X_BACK;
      } else if (xAxis.currentPosition() < -mmToSteps(PUSH_LIMIT_MM + 20)) {
        haltAxis(xAxis);
        task = IDLE;
        Serial.println("ERR HOME");
      }
      break;
    case MOVE_Z:
      // 11/3 밤: 아래에 부딪혀 스텝을 잃은 뒤 ZTOP이 원점을 지나 위로 더 올라갔다.
      // HOME 뒤로는 스위치보다 Z_PARK_MM 아래까지만 가므로, 올라가는 중 스위치가 눌리면 위치가 어긋난 것
      // → 그 자리에서 멈추고 ERR LIMIT (다시 HOME)
      if (zAxis.distanceToGo() < 0 && digitalRead(PIN_LIM_Z) == LOW) {
        zAxis.setCurrentPosition(0);
        homed = false;
        task = IDLE;
        Serial.println("ERR LIMIT");
      } else if (!zAxis.run()) {
        task = IDLE;
        Serial.println(doneReply);
      }
      break;
    case PUSH_APPROACH:
      if (!xAxis.run()) {
        haltAxis(xAxis);
        xAxis.setSpeed(PUSH_SPEED_MM_S * STEPS_PER_MM);
        pushStartMs = lastSampleMs = millis();
        task = PUSHING;
      }
      break;
    case PUSHING:
      runPush();
      break;
    case HOME_X_BACK:
      if (!xAxis.run()) {
        homed = true;
        task = IDLE;
        Serial.println("OK HOME");
      }
      break;
    case RETREAT:
      // X_PARK_MM까지만 물러나므로 스위치가 눌리면 위치가 어긋난 것 → 거기서 멈춤.
      // 힘 결과는 그대로 보내고 homed를 풀어 다음 ZTOP · LIFT · PUSH가 ERR NOTHOMED가 되게 한다
      if (digitalRead(PIN_LIM_X) == LOW) {
        xAxis.setCurrentPosition(0);
        homed = false;
        task = IDLE;
        Serial.println(resultReply);
      } else if (!xAxis.run()) {
        task = IDLE;
        Serial.println(resultReply);
      }
      break;
    case CLAMPING:
      if (millis() - clampStartMs >= clampDurationMs) {
        clampMotor(0, 0);
        task = IDLE;
        Serial.println(doneReply);
      }
      break;
  }

  if (rotBusy && !rotAxis.run()) {
    rotBusy = false;
    Serial.println("OK ROT");
  }
}

void checkStartButton() {
  bool pressed = digitalRead(PIN_START) == LOW;
  if (pressed && !startWasPressed) Serial.println("START");
  startWasPressed = pressed;
}

// ---------- setup / loop ----------

void setup() {
  Serial.begin(SERIAL_BAUD);

  pinMode(PIN_DRV_EN, OUTPUT);
  digitalWrite(PIN_DRV_EN, LOW);
  pinMode(PIN_CLAMP_A, OUTPUT);
  pinMode(PIN_CLAMP_B, OUTPUT);
  clampMotor(0, 0);
  pinMode(PIN_VAC, OUTPUT);
  pinMode(PIN_LIGHT, OUTPUT);
  digitalWrite(PIN_VAC, LOW);
  digitalWrite(PIN_LIGHT, LOW);
  // RP2350 내부 풀다운 결함 → 스위치는 모두 풀업, 눌리면 GND
  pinMode(PIN_LIM_Z, INPUT_PULLUP);
  pinMode(PIN_LIM_X, INPUT_PULLUP);
  pinMode(PIN_COVER, INPUT_PULLUP);
  pinMode(PIN_ESTOP, INPUT_PULLUP);
  pinMode(PIN_START, INPUT_PULLUP);

  zAxis.setPinsInverted(Z_DIR_INVERT, false, false);  // 방향 (config.h)
  xAxis.setPinsInverted(X_DIR_INVERT, false, false);
  zAxis.setMaxSpeed(Z_SPEED_MM_S * STEPS_PER_MM);
  zAxis.setAcceleration(Z_ACCEL_MM_S2 * STEPS_PER_MM);
  xAxis.setMaxSpeed(X_SPEED_MM_S * STEPS_PER_MM);
  xAxis.setAcceleration(X_ACCEL_MM_S2 * STEPS_PER_MM);
  rotAxis.setMaxSpeed(ROT_SPEED_STEPS_S);
  rotAxis.setAcceleration(ROT_ACCEL_STEPS_S2);

  loadcell.begin(PIN_HX_DOUT, PIN_HX_SCK);

  if (IGNORE_SAFETY_INPUTS) Serial.println("WARN SAFETY INPUTS IGNORED");
  Serial.println("READY");
}

void loop() {
  // X 마지노선 (config.h X_HARD_MAX_MM) — 어떤 일이 있어도 넘지 않게 마지막 울타리
  if (!stopped && xAxis.currentPosition() > mmToSteps(X_HARD_MAX_MM)) emergencyStop("ERR XMAX");
  checkSafety();
  readSerial();
  if (!stopped) runTask();
  checkStartButton();
}
