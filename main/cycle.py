"""앰플 한 개 전체 순서 (Pi에서 돈다). 지금은 사진 파일로 노트북에서 돌려 본다. 빈 칸 사진(--bg)은 실물 사진에 필요하다.

    python main/cycle.py --fake --back vision/samples/5ml_back_000_01.jpg --front vision/samples/5ml_front_000_01.jpg --bg vision/samples/bg_back_000_01.jpg
    python main/cycle.py --port auto --back ... --front ... --bg ...     # Pico 연결 후

순서 (노션 제품 스펙 4장, 2차 발표 시제품 = 카트리지는 손으로):
  대기 칸:   찍기 → 규격 · 점 각도 → ROT
  사람:      Z가 맨 위인지 확인(ZTOP) → 카트리지를 한 칸 민다 → 시작 버튼
  파단 위치: LIFT(노치 높이) → CLAMP 1 → VAC 1 → PUSH → CLAMP 0 → VAC 0 → ZTOP
"""

import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vision"))

from detect import analyze  # noqa: E402
from pico_link import FakePico, PicoError, SerialLink, pico_ports, wait_all, wait_for  # noqa: E402

PUSHER_FROM_CAMERA_DEG = 29.0  # TODO 카메라는 −X(푸셔 쪽)에서 29° — 부호는 실물에서 확인
HOLDER_STEP_DEG = 6.0           # 홀더 톱니 한 칸
LOG_DIR = ROOT / "logs"


def target_rotation(dot_deg: float) -> float:
    """점을 푸셔 쪽으로 보내는 회전각 (홀더 톱니 단위로 반올림)."""
    rot = PUSHER_FROM_CAMERA_DEG - dot_deg
    rot = (rot + 180) % 360 - 180  # -180 ~ 180, 가까운 쪽으로
    return round(rot / HOLDER_STEP_DEG) * HOLDER_STEP_DEG


def command(link, line: str, *expect: str, **kw) -> str:
    print(f"  → {line}")
    link.send(line)
    reply = wait_for(link, *expect, **kw)
    print(f"  ← {reply}")
    return reply


def wait_start(link, fake: bool, msg: str):
    print(f"  ⏸ {msg} → 시작 버튼")
    if not fake:
        wait_for(link, "START", timeout=600)


def run_cycle(link, back, front, fake: bool, bg=None) -> dict:
    row = {"time": datetime.now().isoformat(timespec="seconds")}

    # 1. 대기 칸: 판별
    print("[1] 비전")
    r = analyze(back, front, bg=bg)
    if r.size is None or r.size.spec is None:
        print("  빈 칸이거나 규격을 모름 → 건너뜀")
        return {**row, "result": "SKIP_SIZE"}
    spec = r.size.spec
    row["size"] = spec.name
    print(f"  규격 {spec.name} (오차 {r.size.error:.1%})")
    if r.angle is None:
        # 실제 기계: ROT 180 → 다시 찍기 → 그래도 없으면 OPC 아님 (노션 8장 비전 4)
        print("  점 없음 → 180° 돌려 다시 찍어야 함 (파일 모드에서는 여기서 끝)")
        return {**row, "result": "SKIP_DOT"}
    rot = target_rotation(r.angle)
    row.update(dot_deg=round(r.angle, 1), rot_deg=rot)
    print(f"  점 {r.angle:+.1f}° → 회전 {rot:+.0f}°")
    command(link, f"ROT {rot:.1f}", "OK ROT")

    # 2. 이송 (사람)
    print("[2] 이송")
    command(link, "ZTOP", "OK ZTOP")
    wait_start(link, fake, "카트리지를 한 칸 미세요")

    # 3. 파단
    print("[3] 파단")
    command(link, f"LIFT {spec.notch_h:.1f}", "OK LIFT")
    command(link, "CLAMP 1", "OK CLAMP")
    command(link, "VAC 1", "OK VAC")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    force_path = LOG_DIR / f"force_{stamp}_{spec.name}.csv"
    with open(force_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ms", "N", "mm"])
        try:
            reply = command(link, "PUSH", "BROKE", "NOBREAK", on_force=lambda *v: w.writerow(v))
        finally:
            link.send("CLAMP 0")
            link.send("VAC 0")
    row["result"] = reply.split()[0]
    row["force_n"] = reply.split()[1] if reply.startswith("BROKE") else ""
    row["force_csv"] = force_path.name
    print(f"  힘 곡선 → {force_path.relative_to(ROOT)}")

    wait_all(link, "OK CLAMP", "OK VAC")
    command(link, "ZTOP", "OK ZTOP")
    return row


def log_row(row: dict):
    path = LOG_DIR / "cycles.csv"
    fields = ["time", "size", "dot_deg", "rot_deg", "result", "force_n", "force_csv"]
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fields, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fake", action="store_true", help="가짜 Pico")
    g.add_argument("--port", help="Pico 시리얼 포트. auto = 찾아서 쓰기 (맥 /dev/cu.usbmodem*, 윈도우 COM5, Pi /dev/ttyACM0)")
    ap.add_argument("--back", required=True, help="역광 사진")
    ap.add_argument("--front", help="정면광 사진 (없으면 역광 사진으로)")
    ap.add_argument("--bg", help="앰플 없는 빈 칸 사진")
    ap.add_argument("--fake-break", type=float, default=36.0, help="가짜 파단력 N")
    args = ap.parse_args()

    back = cv2.imread(args.back)
    front = cv2.imread(args.front or args.back)
    bg = cv2.imread(args.bg) if args.bg else None
    if back is None or front is None or (args.bg and bg is None):
        raise SystemExit("사진을 못 읽었다")

    port = args.port
    if port == "auto":
        found = pico_ports()
        if not found:
            raise SystemExit("Pico 포트를 못 찾았다 — USB 케이블 확인")
        port = found[0]

    LOG_DIR.mkdir(exist_ok=True)
    link = FakePico(args.fake_break) if args.fake else SerialLink(port)
    if not args.fake:
        time.sleep(2)  # Pico USB 재연결 대기

    try:
        print("[0] 원점")
        command(link, "HOME", "OK HOME")
        row = run_cycle(link, back, front, args.fake, bg)
    except PicoError as e:
        print(f"  ✋ 정지: {e}")
        row = {"time": datetime.now().isoformat(timespec="seconds"), "result": f"STOP {e}"}
    log_row(row)
    print(f"\n결과: {row}")


if __name__ == "__main__":
    main()
