"""앰플 한 개 전체 순서 (Pi에서 돈다). 지금은 사진 파일로 노트북에서 돌려 본다. 빈 칸 사진(--bg)은 실물 사진에 필요하다.

    python main/cycle.py --fake --back vision/samples/5ml_back_000_01.jpg --front vision/samples/5ml_front_000_01.jpg --bg vision/samples/bg_back_000_01.jpg
    python main/cycle.py --port auto --back ... --front ... --bg ...     # Pico 연결 후

순서 (노션 제품 스펙 4장, 카트리지는 손으로):
  대기 칸:   찍기 → 규격 · 점 각도 → ROT
  사람:      Z가 맨 위인지 확인(ZTOP) → 카트리지를 한 칸 민다 → 시작 버튼
  파단 위치: LIFT(노치 높이) → CLAMP 1 → VAC 1 → PUSH → CLAMP 0 → VAC 0 → ZTOP

2차 발표 시연 (--dual, 11/3): 카트리지를 움직이지 않는다. 앰플을 두 자리에 따로 세우고 동시에 돈다.
  사람:      촬영 자리(앞칸)에 앰플 하나, 파단 자리에 앰플 하나(점을 푸셔 쪽으로 손으로 맞춤) → 시작 버튼
  파단 자리: LIFT → CLAMP 1 → VAC 1 → PUSH → CLAMP 0 · VAC 0 → ZTOP     (규격은 --size)
  촬영 자리: 찍기 → 규격 · 점 각도 → ROT (파단 쪽 명령과 같이 돈다 — Pico가 ROT를 따로 받는다)
    python main/cycle.py --fake --dual --size 5ml --back vision/samples/2ml_back_000_01.jpg --bg vision/samples/bg_back_000_01.jpg
"""

import argparse
import csv
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vision"))

from detect import analyze  # noqa: E402
from specs import BY_NAME  # noqa: E402
from pico_link import FakePico, PicoError, SerialLink, pico_ports, wait_all, wait_for  # noqa: E402

PUSHER_FROM_CAMERA_DEG = 29.0  # TODO 카메라는 −X(푸셔 쪽)에서 29° — 부호는 실물에서 확인
# 11/3 CAD v2.5.22: 홀더는 자석 마찰 클러치로 28BYJ와 1:1로 돈다 (톱니 없음) → 6° 반올림을 없앰.
# 28BYJ 한 칸 = 360 / 4096 ≈ 0.09°라 0.1° 단위로 보낸다. 돌린 뒤 다시 찍어 확인하는 것은 Pi 카메라 촬영을 붙일 때
# HOME이 가장 오래 걸릴 때: Z (Z_TRAVEL 40 + 10) 50 mm ÷ 5 mm/s = 10초 + X (desk 50 mm · ampt 31.7 mm) ÷ 3 mm/s = 최대 약 17초.
# 기본 30초로 기다리면 desk 빌드에서 Pico의 ERR HOME보다 '시간 초과'가 먼저 났다 (11/1)
HOME_TIMEOUT_S = 40.0
LOG_DIR = ROOT / "logs"  # 실물 시험 기록 — git에 올린다. --fake는 logs/fake/ (안 올림)


def target_rotation(dot_deg: float) -> float:
    """점을 푸셔 쪽으로 보내는 회전각 (°, 0.1° 단위)."""
    rot = PUSHER_FROM_CAMERA_DEG - dot_deg
    rot = (rot + 180) % 360 - 180  # -180 ~ 180, 가까운 쪽으로
    return round(rot, 1)


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
    print(f"  점 {r.angle:+.1f}° → 회전 {rot:+.1f}°")
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


class CameraSpot:
    """--dual 촬영 자리: 판별은 따로 도는 스레드에서, ROT는 파단 쪽 응답을 기다리는 틈에 보낸다.
    시리얼은 이 프로그램의 한 줄기(메인 스레드)에서만 읽고 쓴다."""

    def __init__(self, link, back, front, bg):
        self.link = link
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.job = self.pool.submit(analyze, back, front, bg=bg)
        self.row: dict = {}
        self.rot_sent = False
        self.rot_done = False
        self.finished = False  # 판별 결과를 받아 처리함

    def tick(self):
        """판별이 끝났으면 결과를 적고, 돌릴 각도가 있으면 ROT를 보낸다 (한 번만)."""
        if self.finished or not self.job.done():
            return
        self.finished = True
        try:
            r = self.job.result()
        except Exception as e:  # 사진 판별이 죽어도 파단 쪽은 계속
            print(f"  [촬영] 판별 오류: {e}")
            self.row["cam_result"] = "ERR"
            return
        if r.size is None or r.size.spec is None:
            print("  [촬영] 빈 칸이거나 규격을 모름 → 안 돌림")
            self.row["cam_result"] = "SKIP_SIZE"
            return
        self.row["cam_size"] = r.size.spec.name
        if r.angle is None:
            print(f"  [촬영] 규격 {r.size.spec.name}, 점 없음 → 안 돌림 (실제 기계: 180° 돌려 다시 찍기)")
            self.row["cam_result"] = "SKIP_DOT"
            return
        rot = target_rotation(r.angle)
        self.row.update(cam_dot_deg=round(r.angle, 1), cam_rot_deg=rot)
        print(f"  [촬영] 규격 {r.size.spec.name}, 점 {r.angle:+.1f}° → ROT {rot:+.1f}")
        self.link.send(f"ROT {rot:.1f}")
        self.rot_sent = True

    def line(self, line: str):
        if line == "OK ROT" and self.rot_sent:
            print("  [촬영] ← OK ROT")
            self.rot_done = True

    def finish(self, timeout: float = 30.0):
        """파단 쪽이 끝난 뒤: 판별 · 회전이 남았으면 마저 기다린다."""
        try:
            self.job.result(timeout=timeout)
        except Exception:
            pass  # tick()이 오류를 적는다
        self.tick()
        if self.rot_sent and not self.rot_done:
            wait_for(self.link, "OK ROT", timeout=timeout, on_line=self.line)
            print("  [촬영] ← OK ROT")
            self.rot_done = True
        self.row.setdefault("cam_result", "ROT" if self.rot_done else "")
        self.pool.shutdown()
        return self.row


def run_dual(link, back, front, fake: bool, bg, spec) -> dict:
    """2차 발표 시연: 파단 자리(규격 spec, 점은 사람이 맞춤)와 촬영 자리를 동시에."""
    row = {"time": datetime.now().isoformat(timespec="seconds"), "size": spec.name}
    wait_start(link, fake, f"촬영 자리와 파단 자리({spec.name}, 점을 푸셔 쪽으로)에 앰플을 하나씩 세우세요")

    cam = CameraSpot(link, back, front, bg)
    kw = {"on_line": cam.line, "on_tick": cam.tick}
    print("[1] 파단 자리 · 촬영 자리 동시")
    command(link, f"LIFT {spec.notch_h:.1f}", "OK LIFT", **kw)
    command(link, "CLAMP 1", "OK CLAMP", **kw)
    command(link, "VAC 1", "OK VAC", **kw)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 여러 번 돌 때 같은 초에 겹치지 않게
    force_path = LOG_DIR / f"force_{stamp}_{spec.name}.csv"
    with open(force_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ms", "N", "mm"])
        try:
            reply = command(link, "PUSH", "BROKE", "NOBREAK", on_force=lambda *v: w.writerow(v), **kw)
        finally:
            link.send("CLAMP 0")
            link.send("VAC 0")
    row["result"] = reply.split()[0]
    row["force_n"] = reply.split()[1] if reply.startswith("BROKE") else ""
    row["force_csv"] = force_path.name
    print(f"  힘 곡선 → {force_path}")

    left = ["OK CLAMP", "OK VAC"]  # 순서 상관없이 둘 다 (wait_all과 같지만 OK ROT를 놓치지 않게)
    while left:
        got = wait_for(link, *left, **kw)
        left = [p for p in left if not got.startswith(p)]
    command(link, "ZTOP", "OK ZTOP", **kw)
    row.update(cam.finish())
    return row


def log_row(row: dict, name: str = "cycles.csv"):
    path = LOG_DIR / name
    fields = ["time", "size", "dot_deg", "rot_deg", "result", "force_n", "force_csv"]
    if name != "cycles.csv":
        fields = ["time", "size", "result", "force_n", "force_csv", "cam_size", "cam_dot_deg", "cam_rot_deg", "cam_result"]
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
    ap.add_argument("--dual", action="store_true", help="2차 발표 시연: 촬영 자리 · 파단 자리에 따로 세워 동시에")
    ap.add_argument("--size", choices=sorted(BY_NAME), help="--dual에서 파단 자리 앰플 규격")
    ap.add_argument("--rounds", type=int, default=1, help="--dual에서 몇 번 돌지 (매번 시작 버튼)")
    args = ap.parse_args()
    if args.dual and not args.size:
        ap.error("--dual에는 --size(파단 자리 앰플 규격)가 필요하다")

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

    global LOG_DIR
    if args.fake:
        LOG_DIR = LOG_DIR / "fake"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    link = FakePico(args.fake_break, rot_s=0.3) if args.fake else SerialLink(port)
    if not args.fake:
        time.sleep(2)  # Pico USB 재연결 대기

    if args.dual:
        run_dual_rounds(link, back, front, args.fake, bg, BY_NAME[args.size], args.rounds)
        return
    try:
        print("[0] 원점")
        command(link, "HOME", "OK HOME", timeout=HOME_TIMEOUT_S)
        row = run_cycle(link, back, front, args.fake, bg)
    except PicoError as e:
        print(f"  ✋ 정지: {e}")
        row = {"time": datetime.now().isoformat(timespec="seconds"), "result": f"STOP {e}"}
    log_row(row)
    print(f"\n결과: {row}")


def run_dual_rounds(link, back, front, fake, bg, spec, rounds):
    try:
        print("[0] 원점")
        command(link, "HOME", "OK HOME", timeout=HOME_TIMEOUT_S)
    except PicoError as e:
        print(f"  ✋ 정지: {e}")
        return
    for i in range(rounds):
        print(f"\n=== {i + 1} / {rounds} ===")
        try:
            row = run_dual(link, back, front, fake, bg, spec)
        except PicoError as e:
            print(f"  ✋ 정지: {e}")
            row = {"time": datetime.now().isoformat(timespec="seconds"), "size": spec.name, "result": f"STOP {e}"}
            log_row(row, "cycles_dual.csv")
            break
        log_row(row, "cycles_dual.csv")
        print(f"결과: {row}")


if __name__ == "__main__":
    main()
