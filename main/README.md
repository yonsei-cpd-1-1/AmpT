# main

Raspberry Pi에서 도는 전체 순서 프로그램. 비전 결과를 받아 Pico에 시리얼 명령을 보낸다.

| 파일 | 내용 |
|---|---|
| `cycle.py` | 앰플 한 개: 판별 → ROT → (사람이 카트리지 밀기) → LIFT · CLAMP · PUSH → 복귀. 결과는 `logs/cycles.csv`, 힘 곡선은 `logs/force_*.csv` |
| `pico_link.py` | `SerialLink`(진짜 Pico) / `FakePico`(부품 없이 시험) — 같은 모양이라 바꿔 끼운다 |

- 지금은 사진 파일을 넣는다 (`--back` · `--front` · `--bg`). Pi 카메라로 바로 찍는 부분은 아직 없어 `tools/pi_shoot.sh`로 찍어서 넘긴다.
- `--port auto`면 Pico 포트를 찾아서 쓴다 (맥 · 윈도우 · Pi 공통).
- `PUSHER_FROM_CAMERA_DEG = 29`의 부호(왼쪽/오른쪽)는 실물에서 확인.
