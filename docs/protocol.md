# Pi ↔ Pico 명령표

USB 시리얼 115200, 텍스트 한 줄(`\n`로 끝남). 기준 문서는 노션 제품 스펙 8장이고, 바꾸면 둘 다 고친다.
Pico는 보이는 영문 · 숫자 · 기호만 받고 제어 문자(Ctrl+C 등)와 한글은 버린다. 백스페이스(0x08 · 0x7F)는 한 글자 지운다 (11/1 펌웨어부터).

## 명령

| Pi → Pico | 뜻 | Pico → Pi |
|---|---|---|
| `HOME` | Z · X 원점 (리밋 스위치). 회전축은 원점이 없다 | `OK HOME` / `ERR HOME` |
| `ZTOP` | Z 캐리지 맨 위 (카트리지 밀기 전 필수) | `OK ZTOP` |
| `INDEX` | 카트리지 1칸 — **2차 발표 시제품에는 없음** (손으로 민다) | `ERR NOTSUPPORTED` |
| `LIFT 42.0` | Z 캐리지를 규격 높이로 (노치 높이 기준, mm) | `OK LIFT` |
| `ROT 137.0` | 대기 칸 홀더 회전 (°, 상대각). `LIFT` 등과 동시에 실행 | `OK ROT` |
| `CLAMP 1` / `CLAMP 0` | 두 조 닫기 / 열기 (N20) | `OK CLAMP` |
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
| `ERR BUSY` | 앞 명령이 아직 동작 중 (`ROT`는 다른 축과 동시에 돌고, `VAC` · `STATUS` · `RESET` · `INDEX`는 언제나 받는다) |
| `ERR STOPPED` | 비상정지 · 덮개 열림 상태. `RESET` 전에는 아무것도 안 함 |
| `ERR NOTHOMED` | `HOME` 전에 `ZTOP` · `LIFT` · `PUSH`를 보냄 (`RESET` 뒤에도 다시 `HOME`) |
| `ERR RANGE` | `LIFT` 높이가 Z 행정 밖 |
| `ERR HOME` | 원점 찾다가 리밋 스위치를 못 만남 |
| `ERR LOADCELL` | 로드셀 값이 안 오거나, 값이 HX711 끝값(±8388608)에 붙음 = 로드셀 선 빠짐 · 보드 고장. `PUSH`를 받았을 때면 밀지 않고 바로, 밀던 중이면 멈추고 후퇴한 뒤 보냄 |
| `ERR NOTSUPPORTED` | `INDEX`처럼 시제품에 없는 기능 |
