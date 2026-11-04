// 책상 시험 스케치 — 본 펌웨어(firmware/ampt)를 올리기 전에 부품을 하나씩 확인한다.
// 핀은 firmware/ampt/config.h와 같다 (바꾸면 둘 다). 시리얼 115200, 한 줄 명령:
//   io            스위치(LIM_Z · LIM_X · START) 상태를 바뀔 때마다 출력 — 켜기/끄기
//   on / off      스텝 드라이버 켜기 / 끄기 (EN)
//   z 1 / z -1    Z 모터 n바퀴 (1/16 마이크로스텝 = 3200 스텝/바퀴)
//   x 1 / x -1    X 모터 n바퀴
//   spin z / spin x / stop   계속 돌리기 (드라이버 전류 맞출 때)
//   lc            로드셀 값 출력 — 켜기/끄기
//   tare          영점 (아무것도 안 올리고)
//   cal 500       지금 올린 무게(g)로 보정 → config.h에 넣을 값 출력
// 보드 LED가 0.5초마다 깜빡이면 살아 있는 것.
// 로드셀이 이상하면 (11/1에 겪은 것):
//   lc 줄 끝에 SATURATED  = 값이 ±8388608에 붙음 → 로드셀 선(E+ E- A+ A-)이나 HX711 보드
//   lc 줄이 아예 안 나옴   = HX711에서 값이 안 옴 → DT(17번 핀) · SCK(19번 핀)가 바뀌었거나 VCC · GND
// 백스페이스는 Pico 쪽에서 지워진다 (맥 화면에는 ␡ 표시가 남는다). Ctrl+C 같은 제어 문자는 버린다.

#include <AccelStepper.h>
#include <HX711.h>

const int PIN_Z_STEP = 2;
const int PIN_Z_DIR = 3;
const int PIN_X_STEP = 4;
const int PIN_X_DIR = 5;
const int PIN_DRV_EN = 6;  // LOW = 드라이버 켜짐
const int PIN_HX_DOUT = 13;
const int PIN_HX_SCK = 14;
const int PIN_LIM_Z = 15;  // 눌리면 LOW (INPUT_PULLUP)
const int PIN_LIM_X = 16;
const int PIN_START = 21;

// 방향: ampt/config.h Z_DIR_INVERT · X_DIR_INVERT와 같게 (11/3 기구에서 X가 반대 → true, 11/4 오후 Z도 반대 → true)
const bool Z_DIR_INVERT = true;
const bool X_DIR_INVERT = true;
const float STEPS_PER_REV = 200.0 * 16;
const float SPEED_REV_S = 2.0;   // 120 rpm
const float ACCEL_REV_S2 = 2.0;
const float G = 9.80665;
const long SATURATED_COUNTS = 8300000;  // ampt/config.h LOADCELL_SATURATED_COUNTS와 같게
const char* SATURATED_HINT = "SATURATED: check loadcell wires E+ E- A+ A-, or HX711 board";
const char* NODATA_HINT = "no data from HX711: check DT=GP13 (pin 17), SCK=GP14 (pin 19), VCC=pin 36, GND";

AccelStepper zAxis(AccelStepper::DRIVER, PIN_Z_STEP, PIN_Z_DIR);
AccelStepper xAxis(AccelStepper::DRIVER, PIN_X_STEP, PIN_X_DIR);
HX711 loadcell;

bool printIo = false;
bool printLc = false;
AccelStepper* spinning = nullptr;
int lastIo = -1;
long tareCounts = 0;
bool tared = false;
float countsPerN = 1000.0;  // cal 전 임시값
unsigned long rateStartMs = 0;
int rateSamples = 0;
float rateHz = 0;
unsigned long lastLcMs = 0;  // lc가 켜진 뒤 마지막으로 값이 온 때
bool lcHintShown = false;
String lineBuf;

bool saturated(long counts) { return labs(counts) >= SATURATED_COUNTS; }

int readIo() {
  return (digitalRead(PIN_LIM_Z) == LOW) | (digitalRead(PIN_LIM_X) == LOW) << 1 | (digitalRead(PIN_START) == LOW) << 2;
}

void printSwitches(int io) {
  Serial.printf("LIM_Z=%s  LIM_X=%s  START=%s\n", io & 1 ? "PRESSED" : "-", io & 2 ? "PRESSED" : "-",
                io & 4 ? "PRESSED" : "-");
}

// HX711을 n번 읽어 평균. 10 Hz 보드면 n=10에 약 1초
long averageCounts(int n) {
  if (!loadcell.wait_ready_timeout(1000)) return LONG_MIN;
  return loadcell.read_average(n);
}

// 11/3 기구에 단 뒤: bench는 원점을 모르니 한 번에 크게 못 가게 한다 (X는 원점에서 16.25 mm가 마지노선, Z는 25 mm)
const float MAX_JOG_REV = 2.0;  // 3 mm
const bool SPIN_DISABLED = true;  // 계속 돌리기는 끝에 부딪힌다 — 모터를 기구에서 뗐을 때만 false

void moveRevs(AccelStepper& axis, const char* name, float revs) {
  spinning = nullptr;
  if (fabs(revs) > MAX_JOG_REV) {
    Serial.printf("ERR too far: max %.1f rev (%.1f mm) per command on the mechanism\n", MAX_JOG_REV, MAX_JOG_REV * 1.5);
    return;
  }
  axis.move(lround(revs * STEPS_PER_REV));
  Serial.printf("%s %+.2f rev\n", name, revs);
}

void handleCommand(String line) {
  line.trim();
  if (line.length() == 0) return;
  int sp = line.indexOf(' ');
  String cmd = sp < 0 ? line : line.substring(0, sp);
  String arg = sp < 0 ? "" : line.substring(sp + 1);
  cmd.toLowerCase();
  arg.trim();

  if (cmd == "help" || cmd == "?") {
    Serial.println("io | on | off | z <rev> | x <rev> | spin z|x | stop | lc | tare | cal <g>");
  } else if (cmd == "io") {
    printIo = !printIo;
    Serial.println(printIo ? "io ON (press switches)" : "io OFF");
    if (printIo) printSwitches(lastIo = readIo());
  } else if (cmd == "on" || cmd == "off") {
    digitalWrite(PIN_DRV_EN, cmd == "on" ? LOW : HIGH);
    Serial.println(cmd == "on" ? "driver ON (EN=LOW)" : "driver OFF (EN=HIGH)");
  } else if (cmd == "z" || cmd == "x") {
    moveRevs(cmd == "z" ? zAxis : xAxis, cmd == "z" ? "Z" : "X", arg.length() ? arg.toFloat() : 1.0);
  } else if (cmd == "spin" && SPIN_DISABLED) {
    Serial.println("ERR spin disabled: motors are on the mechanism (would hit the end)");
  } else if (cmd == "spin") {
    spinning = arg == "x" ? &xAxis : &zAxis;
    spinning->setSpeed(SPEED_REV_S * STEPS_PER_REV);
    Serial.printf("spin %s (stop = stop)\n", arg == "x" ? "X" : "Z");
  } else if (cmd == "stop") {
    spinning = nullptr;
    zAxis.setCurrentPosition(zAxis.currentPosition());
    xAxis.setCurrentPosition(xAxis.currentPosition());
    Serial.println("stopped");
  } else if (cmd == "lc") {
    printLc = !printLc;
    rateStartMs = lastLcMs = millis();
    rateSamples = 0;
    lcHintShown = false;
    Serial.println(printLc ? "loadcell ON" : "loadcell OFF");
  } else if (cmd == "tare") {
    long c = averageCounts(10);
    if (c == LONG_MIN) {
      Serial.printf("ERR LOADCELL (%s)\n", NODATA_HINT);
      return;
    }
    if (saturated(c)) {
      Serial.printf("ERR LOADCELL %s\n", SATURATED_HINT);
      return;
    }
    tareCounts = c;
    tared = true;
    Serial.printf("tare = %ld counts\n", tareCounts);
  } else if (cmd == "cal") {
    float grams = arg.toFloat();
    if (grams <= 0 || !tared) {
      Serial.println("usage: tare (empty) -> put weight -> cal <grams>");
      return;
    }
    long c = averageCounts(10);
    if (c == LONG_MIN || saturated(c)) {
      Serial.printf("ERR LOADCELL (%s)\n", c == LONG_MIN ? NODATA_HINT : SATURATED_HINT);
      return;
    }
    countsPerN = (c - tareCounts) / (grams / 1000.0 * G);
    Serial.printf("counts = %ld, weight = %.1f g = %.3f N\n", c - tareCounts, grams, grams / 1000.0 * G);
    Serial.printf(">> config.h: const float LOADCELL_COUNTS_PER_N = %.1f;\n", countsPerN);
    // 11/1 실측은 45061.9 · 49059.7. 음수면 PUSH 힘이 −로 읽혀 43 N 정지가 안 걸린다
    if (countsPerN < 0) Serial.println("WARN negative: if this load is the PUSH direction, swap A+ and A-");
    else if (countsPerN < 10000) Serial.println("WARN too small: weight touching something, or loadcell not responding");
  } else {
    Serial.println("? unknown — type help");
  }
}

void readSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      handleCommand(lineBuf);
      lineBuf = "";
    } else if (c == '\b' || c == 0x7F) {  // 백스페이스 (맥 0x7F, 윈도우 0x08) → 한 글자 지움
      if (lineBuf.length() > 0) lineBuf.remove(lineBuf.length() - 1);
    } else if (c >= 0x20 && c < 0x7F && lineBuf.length() < 64) {  // 제어 문자 · 한글은 버림
      lineBuf += c;
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(PIN_DRV_EN, OUTPUT);
  digitalWrite(PIN_DRV_EN, HIGH);  // 처음엔 꺼 둠 → on
  // RP2350 내부 풀다운 결함 → 스위치는 풀업, 눌리면 GND
  pinMode(PIN_LIM_Z, INPUT_PULLUP);
  pinMode(PIN_LIM_X, INPUT_PULLUP);
  pinMode(PIN_START, INPUT_PULLUP);

  zAxis.setPinsInverted(Z_DIR_INVERT, false, false);
  xAxis.setPinsInverted(X_DIR_INVERT, false, false);
  zAxis.setMaxSpeed(SPEED_REV_S * STEPS_PER_REV);
  zAxis.setAcceleration(ACCEL_REV_S2 * STEPS_PER_REV);
  xAxis.setMaxSpeed(SPEED_REV_S * STEPS_PER_REV);
  xAxis.setAcceleration(ACCEL_REV_S2 * STEPS_PER_REV);
  loadcell.begin(PIN_HX_DOUT, PIN_HX_SCK);
  Serial.println("READY bench — type help");
}

void loop() {
  readSerial();

  if (spinning) {
    spinning->runSpeed();
  } else {
    zAxis.run();
    xAxis.run();
  }

  if (printIo) {
    int io = readIo();
    if (io != lastIo) printSwitches(lastIo = io);
  }

  if (printLc && loadcell.is_ready()) {
    long c = lround(loadcell.read());
    lastLcMs = millis();
    rateSamples++;
    unsigned long dt = millis() - rateStartMs;
    if (dt >= 2000) {
      rateHz = rateSamples * 1000.0 / dt;
      rateStartMs = millis();
      rateSamples = 0;
    }
    float n = (c - tareCounts) / countsPerN;
    Serial.printf("raw %ld  force %.2f N (%.0f g)  rate %.0f Hz%s%s\n", c, n, n / G * 1000.0, rateHz,
                  saturated(c) ? "  << " : "", saturated(c) ? SATURATED_HINT : "");
  } else if (printLc && !lcHintShown && millis() - lastLcMs > 1500) {
    Serial.println(NODATA_HINT);  // 11/1: DT · SCK를 바꿔 꽂았을 때 줄이 하나도 안 나왔다
    lcHintShown = true;
  }

  static unsigned long lastBlink = 0;
  if (millis() - lastBlink >= 500) {
    lastBlink = millis();
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
  }
}
