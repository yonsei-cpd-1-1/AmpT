"""Pi ↔ Pico 통신 (docs/protocol.md). 진짜 시리얼과 가짜 Pico가 같은 모양이라 바꿔 끼울 수 있다."""

import time
from collections import deque

import serial


class PicoError(Exception):
    pass


class SerialLink:
    def __init__(self, port: str, baud: int = 115200):
        self.ser = serial.Serial(port, baud, timeout=0.05)

    def send(self, line: str):
        self.ser.write((line + "\n").encode())

    def readline(self) -> str | None:
        raw = self.ser.readline()
        return raw.decode(errors="replace").strip() or None


class FakePico:
    """부품 없이 순서 프로그램을 돌려 보는 가짜. PUSH엔 힘이 오르다 break_n에서 깨지는 곡선을 보낸다."""

    def __init__(self, break_n: float = 36.0):
        self.break_n = break_n
        self.out: deque[str] = deque(["READY"])

    def send(self, line: str):
        cmd, *arg = line.split()
        if cmd == "PUSH":
            self._push()
        elif cmd in ("HOME", "ZTOP", "LIFT", "ROT", "CLAMP", "VAC", "RESET"):
            self.out.append(f"OK {cmd}")
        elif cmd == "STATUS":
            self.out.append("STATUS IDLE")
        else:
            self.out.append(f"ERR UNKNOWN {cmd}")

    def _push(self):
        t, x, f = 0.0, 0.0, 0.0
        while f < self.break_n:  # 80 Hz, 5 mm/s, 접촉 후 힘이 선형으로 오른다고 가정
            t += 12.5
            x += 5 * 0.0125
            f = max(0.0, (x - 0.5) * 30)
            self.out.append(f"FORCE {t:.1f},{min(f, self.break_n):.2f},{x:.3f}")
        for f in (3.0, 0.8):
            t += 12.5
            self.out.append(f"FORCE {t:.1f},{f:.2f},{x:.3f}")
        self.out.append(f"BROKE {self.break_n:.1f}")

    def readline(self) -> str | None:
        return self.out.popleft() if self.out else None


def wait_for(link, *prefixes: str, timeout: float = 30.0, on_force=None) -> str:
    """prefixes 중 하나로 시작하는 줄이 올 때까지 읽는다. FORCE 줄은 on_force로 넘긴다."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        line = link.readline()
        if line is None:
            continue
        if line.startswith("FORCE "):
            if on_force:
                on_force(*map(float, line[6:].split(",")))
            continue
        if line in ("ESTOP", "COVER OPEN") or line.startswith("ERR"):
            raise PicoError(line)
        if line.startswith(prefixes):
            return line
    raise PicoError(f"시간 초과: {prefixes}")
