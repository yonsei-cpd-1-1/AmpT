# firmware

Pico 2 제어 코드 (Arduino C++). 모터·로드셀·스위치·안전 정지를 맡는다.

- 스텝모터 4축 (TMC2209): 푸셔 X, Z 캐리지, OPC 회전, 레일 이송
- 클램프 웜기어 DC 모터 2개 (TB6612FNG)
- 로드셀 (HX711, 80 SPS) — 힘이 급락하면 파단으로 보고 즉시 정지·후퇴

라이브러리: AccelStepper, TMCStepper, HX711
