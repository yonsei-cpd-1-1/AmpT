# firmware

Pico 2 제어 코드 (Arduino C++). 모터·로드셀·스위치·안전 정지를 맡는다. 명령은 `docs/protocol.md`.

| 파일 | 내용 |
|---|---|
| `ampt/ampt.ino` | 명령 받기, 축별 동작, 안전 정지 |
| `ampt/config.h` | 핀 · 스텝/mm(2133.3) · 정지값(43 N) 등 숫자 전부. `TODO` = 실측 전 |
| `ampt/break_detector.h` | 파단 판정 (힘 급락 → 파단, 43 N → 안 깨짐). 아두이노와 무관한 순수 C++ |
| `test/test_break_detector.cpp` | 맥에서 파단 판정 시험 |

- 2차 발표 시제품 구성: Z · X = NEMA17 + TMR8 리드 1.5 (STEP/DIR — TMC2209 · A4988 · DRV8825 공통), 회전 = 28BYJ-48 + ULN2003, 클램프 = N20 1개, 로드셀 = 5 kg + HX711 80 Hz
- 덮개 · 비상정지 스위치가 없으면 늘 정지 상태가 되므로 `IGNORE_SAFETY_INPUTS = true`로 시작한다. **스위치를 달면 false.**

라이브러리: AccelStepper, HX711 (Rob Tillaart). TMC2209 UART 설정(TMCStepper)은 드라이버가 정해지면 추가.
