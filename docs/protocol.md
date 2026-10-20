# Pi ↔ Pico 명령표

USB 시리얼 115200, 텍스트 한 줄(`\n`로 끝남). 기준 문서는 노션 제품 스펙 8장이고, 바꾸면 둘 다 고친다.

## 명령

| Pi → Pico | 뜻 | Pico → Pi |
|---|---|---|
| `HOME` | 전 축 원점 (Z · X는 리밋 스위치) | `OK HOME` / `ERR HOME` |
| `ZTOP` | Z 캐리지 맨 위 (카트리지 밀기 전 필수) | `OK ZTOP` |
| `INDEX` | 카트리지 1칸 — **2차 발표 시제품에는 없음** (손으로 민다) | `ERR NOTSUPPORTED` |
| `LIFT 42.0` | Z 캐리지를 규격 높이로 (노치 높이 기준, mm) | `OK LIFT` |
| `ROT 137.0` | 대기 칸 홀더 회전 (°, 상대각). `LIFT` 등과 동시에 실행 | `OK ROT` |
| `CLAMP 1` / `CLAMP 0` | 두 조 닫기 / 열기 (N20) | `OK CLAMP` |
| `PUSH` | 파단 시도 | `BROKE 36.2` (파단력 N) / `NOBREAK` (정지값 43 N) / `NOBREAK LIMIT` (위치 제한) |
| `VAC 1` / `VAC 0` | 청소기 켜기 / 끄기 | `OK VAC` |
| `STATUS` | 상태 묻기 | `STATUS IDLE` / `STATUS BUSY` / `STATUS STOPPED` |
| `RESET` | 정지 상태 풀기 (비상정지 · 덮개가 정상일 때만) | `OK RESET` |
| — | 언제든 먼저 보냄 | `ESTOP` · `COVER OPEN` |
| — | 시작 버튼을 누름 | `START` |
| — | 켜졌을 때 | `READY` (덮개·비상정지 입력을 무시하는 책상 시험 모드면 앞에 `WARN SAFETY INPUTS IGNORED`) |

## 힘 기록

`PUSH` 중에는 로드셀 샘플마다(80 Hz) 한 줄씩 보낸다. Pi가 CSV로 저장한다.

```
FORCE <ms>,<N>,<mm>
FORCE 12.5,3.41,0.062
```

- `ms` = PUSH 시작 후 시간, `N` = 힘, `mm` = 푸셔 X 변위
- 파단 판정은 Pico가 직접 한다. Pi는 `BROKE` / `NOBREAK`만 보고 다음으로 간다.

## 오류

| 줄 | 뜻 |
|---|---|
| `ERR UNKNOWN <명령>` | 모르는 명령 |
| `ERR BUSY` | 앞 명령이 아직 동작 중 (`ROT`는 예외 — 다른 축과 동시) |
| `ERR STOPPED` | 비상정지 · 덮개 열림 상태. `RESET` 전에는 아무것도 안 함 |
| `ERR NOTHOMED` | `HOME` 전에 `ZTOP` · `LIFT` · `PUSH`를 보냄 (`RESET` 뒤에도 다시 `HOME`) |
| `ERR RANGE` | `LIFT` 높이가 Z 행정 밖 |
| `ERR HOME` | 원점 찾다가 리밋 스위치를 못 만남 |
| `ERR LOADCELL` | 로드셀 값이 안 옴 (PUSH 중이면 멈추고 후퇴한 뒤 보냄) |
