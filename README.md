# AmpT — 유리 앰플 자동 개봉기

연세대학교 기계공학부 창의제품설계(종합설계) 1분반 1조

OPC 유리 앰플을 한 개씩 자동으로 굽혀 따고, 파편은 그 자리에서 흡입하는 장비의 소프트웨어 저장소.

## 구조

| 폴더 | 내용 | 언어 |
|---|---|---|
| `firmware/` | Pico 2 제어 코드 — Z · X 스텝모터, 회전 28BYJ, 클램프 N20, 로드셀, 안전 | Arduino C++ |
| `vision/` | OPC 점·규격 인식 | Python + OpenCV |
| `main/` | Pi에서 도는 전체 순서 프로그램 | Python |
| `tools/` | Pico 굽기 · 시리얼 창 · 촬영 스크립트 | Python · 셸 |
| `docs/` | 핀 배치표(`pins.md`), 통신 명령표(`protocol.md`), **사용 가이드(`AmpT_사용가이드.pdf`)** | — |

## 처음 세팅

필요한 것: Python 3.10 이상, Git, arduino-cli. 맥은 `brew install arduino-cli`, 윈도우는 공식 MSI를 쓴다.

```bash
# 맥
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
tools/pico.sh setup    # 보드 코어 · 라이브러리 설치
tools/pico.sh doctor   # 점검
```

```bat
:: 윈도우 — 저장소를 C:\AmpT처럼 한글 없는 경로에 clone 한다 (컴파일러가 한글 경로를 못 읽는다)
py -3 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\tools\pico setup
.\tools\pico doctor
```

윈도우에서는 `.venv/bin/python` 대신 `.\.venv\Scripts\python`, `tools/pico.sh` 대신 `.\tools\pico`를 쓴다.

## 자주 쓰는 명령

```bash
# 시험
.venv/bin/python -m pytest vision/tests main/tests           # 비전 (가짜 앰플 그림) · Pico 응답 대기
clang++ -std=c++17 firmware/test/test_break_detector.cpp -o /tmp/tb && /tmp/tb   # 파단 판정

# 비전
.venv/bin/python vision/live.py --list                       # 카메라 번호 찾기 (아이폰 연속성 카메라 포함)
.venv/bin/python vision/live.py --camera 1 --prefix 5ml_000  # 미리보기, b/f로 역광/정면광 저장
.venv/bin/python vision/detect.py vision/samples/ --bg vision/samples/bg_back_000_01.jpg --debug vision/samples/debug
.venv/bin/python vision/calib.py vision/samples/calib_*.jpg -o vision/calib.npz
bash ~/AmpT/tools/pi_shoot.sh 5ml_000                        # (Pi에서) Pi 카메라로 역광 · 정면광 한 쌍 → ~/samples/

# 펌웨어 — 처음 한 번은 BOOTSEL을 누른 채 USB를 꽂는다. 기구에 달 때는 bench로 방향을 본 뒤 ampt (desk 금지)
tools/pico.sh flash bench    # 책상 시험 스케치 (스위치 · 모터 n바퀴 · 로드셀 보정)
tools/pico.sh flash desk     # 본 펌웨어, 책상 모드 (-DDESK_TEST: PUSH 위치 제한 30 mm)
tools/pico.sh flash ampt     # 본 펌웨어
tools/pico.sh term           # 시리얼 창 — HOME, STATUS 등을 직접 쳐 보기, 끝내기 Ctrl+]

# 전체 순서 (부품 없이 가짜 Pico로)
.venv/bin/python main/cycle.py --fake --back <역광.jpg> --front <정면광.jpg> --bg <빈칸.jpg>
.venv/bin/python main/cycle.py --port auto --back <역광.jpg> --front <정면광.jpg> --bg <빈칸.jpg>   # Pico 연결
```

- 숫자(스텝/mm, 정지값 43 N, 핀 등)는 `firmware/ampt/config.h`, 비전 조정값은 `vision/config.py`에 모았다. `TODO`는 실측 · 확인 전 값. `firmware/bench/bench.ino`는 같은 핀을 따로 적고, 앰플 치수는 `vision/specs.py`, 카메라 각도는 `main/cycle.py`에 있다.
- 시험 사진(`vision/samples/`)은 저장소에 들어 있다. 로그(`logs/`)와 판별 그림(`vision/samples/debug/`)은 올리지 않는다.

## 규칙

1. 작업 전에 항상 Pull.
2. 커밋 메시지는 한 일을 한 줄로. 예: `로드셀 80SPS 읽기 추가`
3. 큰 작업은 브랜치를 따로 만든다.
4. CAD 원본, 대용량 사진·영상, 비밀번호는 올리지 않는다.
5. 명령어·핀 번호를 바꾸면 노션의 제품 스펙 문서와 `docs/`를 같이 고친다.
