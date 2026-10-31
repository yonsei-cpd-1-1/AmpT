# Pico 2 핀 배치 (임시)

> **전장 담당과 확정 전 임시안.** 바꾸면 `firmware/ampt/config.h`도 같이 고친다.
> 입력은 모두 `INPUT_PULLUP` (RP2350 내부 풀다운 결함). 리밋 · 시작은 눌리면 LOW, 덮개는 닫히면 LOW, 비상정지는 평소 LOW이고 눌리면 HIGH.
> 물리 핀 번호와 실제 배선은 사용 가이드(`AmpT_사용가이드.pdf`)의 배선 지도를 본다.

| GPIO | 이름 | 연결 | 비고 |
|---|---|---|---|
| 2 | Z_STEP | Z 드라이버 STEP | NEMA17 + TMR8 리드 1.5 |
| 3 | Z_DIR | Z 드라이버 DIR | |
| 4 | X_STEP | X 드라이버 STEP | 푸셔 |
| 5 | X_DIR | X 드라이버 DIR | |
| 6 | DRV_EN | 두 드라이버 EN | LOW = 켜짐 |
| 7 | ROT_IN1 | ULN2003 IN1 | 28BYJ-48 |
| 8 | ROT_IN2 | ULN2003 IN2 | |
| 9 | ROT_IN3 | ULN2003 IN3 | |
| 10 | ROT_IN4 | ULN2003 IN4 | |
| 11 | CLAMP_A | DC 드라이버 IN1 (PWM) | N20 |
| 12 | CLAMP_B | DC 드라이버 IN2 (PWM) | |
| 13 | HX_DOUT | HX711 DOUT | 지금 보드는 약 10 Hz. 80 Hz는 칩 15번 다리를 16번으로 옮기는 개조가 필요 |
| 14 | HX_SCK | HX711 SCK | |
| 15 | LIM_Z | Z 리밋 스위치 | 위쪽 원점 |
| 16 | LIM_X | X 리밋 스위치 | 뒤쪽 원점 |
| 17 | VAC | 청소기 MOSFET | |
| 18 | LIGHT | 조명 MOSFET | |
| 19 | COVER | 덮개 스위치 | 열리면 정지 |
| 20 | ESTOP | 비상정지 신호 | 12 V는 스위치가 직접 끊음 |
| 21 | START | 시작 버튼 | |

남는 핀: 0 · 1, 22, 26~28. 이 핀들과 GP17~20은 아직 헤더를 땜하지 않았다.
