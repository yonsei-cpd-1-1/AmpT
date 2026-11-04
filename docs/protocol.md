# Pi ↔ Pico 명령표

USB 시리얼 115200, 텍스트 한 줄(`\n`로 끝남). 기준 문서는 노션 제품 스펙 8장이고, 바꾸면 둘 다 고친다.
Pico는 보이는 영문 · 숫자 · 기호만 받고 제어 문자(Ctrl+C 등)와 한글은 버린다. 백스페이스(0x08 · 0x7F)는 한 글자 지운다 (11/1 펌웨어부터).

## 명령

| Pi → Pico | 뜻 | Pico → Pi |
|---|---|---|
| `HOME` | Z · X 원점 (리밋 스위치). Z는 스위치에 닿아 0을 잡은 뒤 바로 `Z_PARK_MM`(5 mm) 내려오고, 그다음 X도 스위치에 닿은 뒤 `X_PARK_MM`(5 mm) 앞으로 나온다. 회전축은 원점이 없다 | `OK HOME` / `ERR HOME` |
| `ZTOP` | Z 캐리지 맨 위 = 원점 스위치보다 `Z_PARK_MM`(5 mm) 아래 (카트리지 밀기 전 필수). 스위치 높이까지는 `HOME` 때만 간다 | `OK ZTOP` |
| `INDEX` | 카트리지 1칸 — **2차 발표 시제품에는 없음** (손으로 민다) | `ERR NOTSUPPORTED` |
| `LIFT 42.0` | Z 캐리지를 규격 높이로 (노치 높이 기준, mm) | `OK LIFT` |
| `ROT 137.0 [deg/s]` | 대기 칸 홀더 회전 (°, 상대각). `LIFT` 등과 동시에 실행. HOME 없이 됨. 속도를 붙이면 5~180 °/s (가속은 0.5 s에 최고 속도), 없으면 **120 °/s** (11/4 기구에서 정함, 그 전 약 70) | `OK ROT` / `ERR SPEED (5~180 deg/s)` |
| `CLAMP 1` / `CLAMP 0` | 두 조 닫기 / 열기 (N20) | `OK CLAMP` |
| `CJOG <ms> [pwm]` | **시험용** 클램프 조금씩: + 닫기 · − 열기 (최대 4000 ms, pwm 기본 `CLAMP_PWM`), `CJOG 0` = 누적 지우기. HOME 없이 됨. **`ROT`처럼 Z · X와 따로 돈다** (11/4) → CJOG 중에도 `XJOG` 등을 받고, 그 반대도 된다. 같은 N20인 `CLAMP`와는 서로 `ERR BUSY` | `OK CJOG +50 ms pwm 128, total +350 ms` (끝났을 때) |
| `ZJOG <mm> [mm/s]` · `XJOG <mm> [mm/s]` | **시험용** 지금 자리에서 Z · X를 mm만큼 (Z + = 아래, X + = 앰플 쪽). 속도 0.1~10 mm/s, 없으면 2 mm/s. HOME 뒤에만. 갈 수 있는 곳: Z 5 ~ 30.25 mm, X 5 ~ 30 mm (원점 스위치 기준, 마지노선 그대로. **X 30은 11/4 임시**) | `OK ZJOG Z 12.000 X 5.000 mm` |
| `ZGO <mm> [mm/s]` · `XGO <mm> [mm/s]` | **시험용** 원점 스위치에서 그 위치로 (범위 · 속도는 위와 같음) | `OK XGO Z 12.000 X 8.900 mm` |
| `STOP` | **시험용** 도는 Z · X · 회전 · 클램프 · `GRIP1` · `BREAK1`을 그 자리에서 멈춤 (BUSY여도 받음). 위치는 그대로라 HOME 다시 안 해도 됨 (HOME 도중이면 다시) | `OK STOP Z … X … mm` |
| `POS` | 지금 위치 (원점 스위치에서 mm) | `POS Z 12.000 X 5.000 mm` |
| `GRIP1` | **시험용** 1 mL 잡기 (11/4): `XGO 5` → `ZGO 21.5` → `CJOG 3000 255` → `XGO 9.5`. 값은 `config.h` `GRIP1_*`. HOME 뒤에만, **클램프가 열린 상태에서** (시간으로만 조인다) | 단계별 `OK XGO …` · `OK ZGO …` · `OK CJOG …` 다음 `OK GRIP1` / 단계가 못 시작하면 `ERR GRIP1` |
| `BREAK1` | **시험용** 1 mL 파단 (11/4 09:38 이 값으로 깨짐): `GRIP1` 상태에서 `CJOG 3500 255`와 `XGO 21.5 5`를 **동시에**. 로드셀 판정 없음 | `OK CJOG …` · `OK XGO …` 다음 `OK BREAK1` / `ERR BREAK1` |
| `RETREAT1` | **시험용** 1 mL 후퇴: 클램프를 열면서(`CJOG -4000`) 동시에 `XGO 5.0`(잡기 자리보다 3바퀴 뒤), 이어서 남은 `CJOG -3500`. 여는 시간 7500 ms = 잡기 3000 + 파단 3500 + 여유 1000 (`RETREAT1_CLAMP_EXTRA_MS`) → `GRIP1` 전보다 1000 ms 더 열린 상태. 순서: `GRIP1` → `BREAK1` → `RETREAT1` | `OK CJOG …` · `OK XGO …` · `OK CJOG …` 다음 `OK RETREAT1` / `ERR RETREAT1` |
| `ALIGN1` | **시험용** 다음 앰플(2 mL) 높이로: `ZGO 12.5` (Z만, `config.h` `ALIGN1_Z_MM`). 전체 순서: `HOME` → `GRIP1` → `BREAK1` → `RETREAT1` → `ALIGN1` | `OK ZGO …` 다음 `OK ALIGN1` / `ERR ALIGN1` |
| `PUSH` | 파단 시도 | `BROKE 36.2` (파단력 N) / `NOBREAK` (정지값 43 N) / `NOBREAK LIMIT` (위치 제한) |
| `VAC 1` / `VAC 0` | 청소기 켜기 / 끄기 | `OK VAC` |
| `STATUS` | 상태 묻기 | `STATUS IDLE` / `STATUS BUSY` / `STATUS STOPPED` |
| `RESET` | 정지 상태 풀기 (비상정지 · 덮개가 정상일 때만). 도는 동작을 멈추지는 않고, 다음에 다시 `HOME`이 필요 | `OK RESET` |
| — | 언제든 먼저 보냄 | `ESTOP` · `COVER OPEN` |
| — | 시작 버튼을 누름 | `START` |
| — | 켜졌을 때 | `READY` (덮개 · 비상정지 입력을 무시하는 동안은 앞에 `WARN SAFETY INPUTS IGNORED`, 지금은 모든 빌드가 해당) |

## 힘 기록

`PUSH` 중에는 로드셀 샘플마다 한 줄씩 보낸다 (지금 보드 약 10 Hz, 개조 후 80 Hz). Pi가 CSV로 저장한다.

```
FORCE <ms>,<N>,<mm>
FORCE 96,3.41,0.062
```

- `ms` = PUSH 시작 후 시간, `N` = 힘, `mm` = 푸셔 X 변위
- 파단 판정은 Pico가 직접 한다. Pi는 `BROKE` / `NOBREAK`만 보고 다음으로 간다.

## 오류

| 줄 | 뜻 |
|---|---|
| `ERR UNKNOWN <명령>` | 모르는 명령 |
| `ERR BUSY` | 앞 명령이 아직 동작 중 (`ROT` · `CJOG`는 다른 축과 동시에 돌고, `VAC` · `STATUS` · `RESET` · `INDEX`는 언제나 받는다) |
| `ERR STOPPED` | 비상정지 · 덮개 열림 상태. `RESET` 전에는 아무것도 안 함 |
| `ERR NOTHOMED` | `HOME` 전에 `ZTOP` · `LIFT` · `PUSH`를 보냄 (`RESET` 뒤에도 다시 `HOME`) |
| `ERR RANGE Z 33.000 (5.00~30.25 mm)` | `ZJOG` · `ZGO` · `XJOG` · `XGO` 목표가 범위 밖 — 안 움직임 |
| `ERR SPEED (0.1~10.0 mm/s)` | 시험용 이동 속도가 범위 밖 |
| `ERR LIMIT` | 올라가거나 물러나는 중 원점 스위치가 눌림 = 위치가 어긋남 → 멈추고 다시 `HOME` |
| `ERR RANGE` | `LIFT` 높이가 Z 행정 밖 (원점에서 `Z_PARK_MM` ~ `Z_TRAVEL_MM` = 5 ~ 30.25 mm → `LIFT 57` ~ `LIFT 31.75`) |
| `ERR HOME` | 원점 찾다가 리밋 스위치를 못 만남 |
| `ERR LIMIT` | `LIFT` · `ZTOP`으로 올라가던 중 Z 원점 스위치가 눌림 = 위치가 어긋남 (부딪혀 스텝을 잃음 등). 그 자리에서 멈춤, 다시 `HOME` 필요. PUSH 후퇴는 `X_PARK_MM`까지만 물러나고, 그 사이 X 스위치가 눌리면 멈춘 뒤 결과 줄은 그대로 보내되 HOME을 풀어 다음 `ZTOP` 등이 `ERR NOTHOMED`가 된다 |
| `ERR LOADCELL` | 로드셀 값이 안 오거나, 값이 HX711 끝값(±8388608)에 붙음 = 로드셀 선 빠짐 · 보드 고장. `PUSH`를 받았을 때면 밀지 않고 바로, 밀던 중이면 멈추고 후퇴한 뒤 보냄 |
| `ERR NOTSUPPORTED` | `INDEX`처럼 시제품에 없는 기능 |
| `ERR XMAX` | X가 마지노선 `X_HARD_MAX_MM`(원점 스위치에서 16.25 mm였고 **11/4 임시 30 mm**. 11/3 기록은 16.25 앞에서 MGN 블록이 레일을 벗어난다고 함)을 넘음 → 비상정지 (드라이버 끔). `RESET` → `HOME`. 정상이면 `PUSH_LIMIT_MM`에서 먼저 멈추므로 나오지 않는다 |
| `ERR ZMAX` | Z가 마지노선 `Z_HARD_MAX_MM`(원점 스위치에서 30.25 mm 아래 = `LIFT 31.75`. 11/4 32 mm에서 부딪혀 31로 정했다가, 31에서도 닿아 30.25)을 넘음 → 비상정지 (드라이버 끔). `RESET` → `HOME`. 정상이면 `LIFT` 범위(`ERR RANGE`)에서 먼저 막히므로 나오지 않는다 |
