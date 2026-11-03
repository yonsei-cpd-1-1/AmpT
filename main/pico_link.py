"""Pi ↔ Pico 통신 (docs/protocol.md). 진짜 시리얼과 가짜 Pico가 같은 모양이라 바꿔 끼울 수 있다."""

import time
from collections import deque

import serial
from serial.tools import list_ports

PICO_VID = 0x2E8A


class PicoError(Exception):
    pass


def pico_ports() -> list[str]:
    """꽂혀 있는 Pico의 시리얼 포트 (맥 /dev/cu.usbmodem…, 윈도우 COM5, Pi /dev/ttyACM0)."""
    return [p.device for p in list_ports.comports() if p.vid == PICO_VID]


class SerialLink:
    def __init__(self, port: str, baud: int = 115200):
        self.ser = serial.Serial(port, baud, timeout=0.05)

    def send(self, line: str):
        self.ser.write((line + "\n").encode())

    def readline(self) -> str | None:
        raw = self.ser.readline()
        return raw.decode(errors="replace").strip() or None


class FakePico:
    """부품 없이 순서 프로그램을 돌려 보는 가짜. PUSH엔 힘이 오르다 break_n에서 깨지는 곡선을 보낸다.
    진짜처럼 CLAMP · ROT는 시간이 지나야 답하고, 그 사이 다른 명령은 바로 답한다
    (진짜 Pico도 ROT는 LIFT · CLAMP · PUSH와 따로 돈다)."""

    def __init__(self, break_n: float = 36.0, clamp_s: float = 0.05, rot_s: float = 0.0):
        self.break_n = break_n
        self.clamp_s = clamp_s
        self.rot_s = rot_s
        self.out: deque[str] = deque(["READY"])
        self.later: list[tuple[float, str]] = []

    def send(self, line: str):
        cmd, *arg = line.split()
        if cmd == "PUSH":
            self._push()
        elif cmd == "CLAMP":
            self._later(self.clamp_s, "OK CLAMP")
        elif cmd == "ROT" and self.rot_s > 0:
            self._later(self.rot_s, "OK ROT")
        elif cmd in ("HOME", "ZTOP", "LIFT", "ROT", "VAC", "RESET"):
            self.out.append(f"OK {cmd}")
        elif cmd == "STATUS":
            self.out.append("STATUS IDLE")
        else:
            self.out.append(f"ERR UNKNOWN {cmd}")

    def _push(self):
        t, x, f = 0.0, 0.0, 0.0
        while f < self.break_n:  # 80 Hz, 2 mm/s (config.h PUSH_SPEED_MM_S), 접촉 후 힘이 선형으로 오른다고 가정
            t += 12.5
            x += 2 * 0.0125
            f = max(0.0, (x - 0.5) * 30)
            self.out.append(f"FORCE {t:.1f},{min(f, self.break_n):.2f},{x:.3f}")
        for f in (3.0, 0.8):
            t += 12.5
            self.out.append(f"FORCE {t:.1f},{f:.2f},{x:.3f}")
        self.out.append(f"BROKE {self.break_n:.1f}")

    def _later(self, delay_s: float, line: str):
        self.later.append((time.monotonic() + delay_s, line))
        self.later.sort()

    def readline(self) -> str | None:
        while self.later and self.later[0][0] <= time.monotonic():
            self.out.append(self.later.pop(0)[1])
        return self.out.popleft() if self.out else None


def wait_for(link, *prefixes: str, timeout: float = 30.0, on_force=None, on_line=None, on_tick=None) -> str:
    """prefixes 중 하나로 시작하는 줄이 올 때까지 읽는다. FORCE 줄은 on_force로 넘긴다.
    기다리지 않는 줄은 버리는데, on_line이 있으면 그리로 넘긴다 (예: PUSH를 기다리는 사이 온 OK ROT).
    on_tick은 줄을 읽기 전마다 부른다 (기다리는 동안 다른 명령을 보낼 때)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if on_tick:
            on_tick()
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
        if on_line:
            on_line(line)
    raise PicoError(f"시간 초과: {prefixes}")


def wait_all(link, *prefixes: str, timeout: float = 30.0) -> None:
    """prefixes가 모두 올 때까지 읽는다. 순서는 상관없다 (VAC는 바로, CLAMP는 1.5초 뒤 답한다)."""
    left = list(prefixes)
    while left:
        got = wait_for(link, *left, timeout=timeout)
        left = [p for p in left if not got.startswith(p)]
