# AmpT — 유리 앰플 자동 개봉기

연세대학교 기계공학부 창의제품설계(종합설계) 1분반 1조

OPC 유리 앰플을 한 개씩 자동으로 굽혀 따고, 파편은 그 자리에서 흡입하는 장비의 소프트웨어 저장소.

## 구조

| 폴더 | 내용 | 언어 |
|---|---|---|
| `firmware/` | Pico 2 제어 코드 — Z · X 스텝모터, 회전 28BYJ, 클램프 N20, 로드셀, 안전 | Arduino C++ |
| `vision/` | OPC 점·규격 인식 | Python + OpenCV |
| `main/` | Pi에서 도는 전체 순서 프로그램 | Python |
| `tools/` | 시험·보정·분석 스크립트 | Python |
| `docs/` | 핀 배치표(`pins.md`), 통신 명령표(`protocol.md`) | — |

## 처음 세팅 (맥)

```bash
# Python (비전 · 순서 프로그램)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Pico 펌웨어 (arduino-cli, Arduino IDE도 같은 보드·라이브러리)
arduino-cli config add board_manager.additional_urls \
  https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json
arduino-cli core update-index
arduino-cli core install rp2040:rp2040
arduino-cli lib install AccelStepper HX711
```

## 자주 쓰는 명령

```bash
# 시험
.venv/bin/python -m pytest vision/tests                      # 비전 (가짜 앰플 그림)
clang++ -std=c++17 firmware/test/test_break_detector.cpp -o /tmp/tb && /tmp/tb   # 파단 판정

# 비전
.venv/bin/python vision/live.py --list                       # 카메라 번호 찾기 (아이폰 연속성 카메라 포함)
.venv/bin/python vision/live.py --camera 1 --prefix 5ml_000  # 미리보기, b/f로 역광/정면광 저장
.venv/bin/python vision/detect.py vision/samples/ --debug vision/samples/debug
.venv/bin/python vision/calib.py vision/samples/calib_*.jpg -o vision/calib.npz

# 펌웨어
arduino-cli compile --fqbn rp2040:rp2040:rpipico2 firmware/ampt
arduino-cli upload  --fqbn rp2040:rp2040:rpipico2 -p /dev/cu.usbmodem* firmware/ampt
arduino-cli monitor -p /dev/cu.usbmodem* -c baudrate=115200   # HOME, STATUS 등을 직접 쳐 보기

# 전체 순서 (부품 없이 가짜 Pico로)
.venv/bin/python main/cycle.py --fake --back <역광.jpg> --front <정면광.jpg>
```

- 숫자(스텝/mm, 정지값 43 N, 핀 등)는 `firmware/ampt/config.h`, 비전 조정값은 `vision/config.py` 한곳에만 있다. `TODO`는 실측 · 확인 전 값.
- 사진(`vision/samples/`)과 로그(`logs/`)는 git에 올리지 않는다.

## 규칙

1. 작업 전에 항상 Pull.
2. 커밋 메시지는 한 일을 한 줄로. 예: `로드셀 80SPS 읽기 추가`
3. 큰 작업은 브랜치를 따로 만든다.
4. CAD 원본, 대용량 사진·영상, 비밀번호는 올리지 않는다.
5. 명령어·핀 번호를 바꾸면 노션의 제품 스펙 문서와 `docs/`를 같이 고친다.
