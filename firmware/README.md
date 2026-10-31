# firmware

Pico 2 제어 코드 (Arduino C++). 모터·로드셀·스위치·안전 정지를 맡는다. 명령은 `docs/protocol.md`.

| 파일 | 내용 |
|---|---|
| `ampt/ampt.ino` | 명령 받기, 축별 동작, 안전 정지 |
| `ampt/config.h` | 핀 · 스텝/mm(2133.3) · 정지값(43 N) 등 숫자 전부. `TODO` = 실측 전 |
| `ampt/break_detector.h` | 파단 판정 (힘 급락 → 파단, 43 N → 안 깨짐). 아두이노와 무관한 순수 C++ |
| `test/test_break_detector.cpp` | 노트북에서 파단 판정 시험 |
| `bench/bench.ino` | 책상 시험 스케치 — 스위치 상태, 모터 n바퀴 · 연속 회전(전류 맞추기), 로드셀 영점 · 보정값. 핀은 `config.h`와 같게 |

- 책상 시험 모드: `-DDESK_TEST`로 컴파일하면 PUSH 위치 제한이 30 mm (로드셀을 손으로 눌렀다 뗄 시간). `tools/pico.sh flash desk` (윈도우 `tools\pico flash desk`). 기구에 달 때는 쓰지 않는다

- 2차 발표 시제품 구성: Z · X = NEMA17 + TMR8 리드 1.5 (STEP/DIR, 드라이버 DRV8825), 회전 = 28BYJ-48 + ULN2003, 클램프 = N20 1개, 로드셀 = 5 kg + HX711 (지금 보드는 약 10 Hz, 80 Hz는 개조 후)
- 덮개 · 비상정지 스위치가 없으면 늘 정지 상태가 되므로 `IGNORE_SAFETY_INPUTS = true`로 시작한다. **스위치를 달면 false.** 이 값은 `ampt` · `desk` 빌드 모두 같다.
- 정지 명령이 없다. 멈추려면 12 V와 Pico USB를 둘 다 뽑는다. `RESET`은 도는 동작을 멈추지 못한다.

라이브러리: AccelStepper 1.64, HX711 0.6.3 (Rob Tillaart). `tools/pico.sh setup`이 설치한다.
