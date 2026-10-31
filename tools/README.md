# tools

Pico 굽기 · 시리얼 창 · 촬영 스크립트.

| 파일 | 어디서 | 내용 |
|---|---|---|
| `pico.py` | 맥 · 윈도우 | `setup` = arduino-cli 코어 · 라이브러리 설치, `doctor` = 설치 · 연결 점검, `flash bench · desk · ampt` = 컴파일해서 Pico 2에 굽기, `term` = 시리얼 창 |
| `pico.sh` | 맥 | `pico.py`를 `.venv`로 부른다. `tools/pico.sh doctor` |
| `pico.bat` | 윈도우 | `pico.py`를 `.venv`로 부른다. `tools\pico doctor` |
| `pi_shoot.sh` | Pi | 카메라 모듈 3로 사진 찍기. 이름은 `vision/detect.py` 규칙 (`5ml_back_000_01.jpg`). 초점은 `LENS`로 고정 (기본 6.25 = 16 cm) |
