"""Pico 2 펌웨어 굽기 · 시리얼 창 · 개발 환경 점검 (맥 · 윈도우 공용).

맥은 tools/pico.sh <명령>, 윈도우(PowerShell · cmd)는 .\\tools\\pico <명령>으로 부른다.

    setup         arduino-cli로 보드 코어 · 라이브러리 설치 (처음 한 번)
    doctor        설치 · 연결 상태 점검
    flash bench   책상 시험 스케치 (firmware/bench)
    flash desk    본 펌웨어, 책상 시험 모드 (PUSH 위치 제한 30 mm, DESK_TEST)
    flash ampt    본 펌웨어 (기구에 달 때)
    term          시리얼 창 — 명령 치고 Enter, 끝내기 Ctrl+]

처음 한 번은 BOOTSEL 버튼을 누른 채 USB를 꽂는다. 그 뒤로는 그냥 flash.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "main"))

FQBN = "rp2040:rp2040:rpipico2"
BOARD_URL = "https://github.com/earlephilhower/arduino-pico/releases/download/global/package_rp2040_index.json"
CORE = ("rp2040:rp2040", "6.3.0")
LIBS = (("AccelStepper", "1.64"), ("HX711", "0.6.3"))
BUILDS = {
    "bench": ("firmware/bench", "bench.ino.uf2", []),
    "desk": ("firmware/ampt", "ampt.ino.uf2", ["--build-property", "compiler.cpp.extra_flags=-DDESK_TEST"]),
    "ampt": ("firmware/ampt", "ampt.ino.uf2", []),
}
WINDOWS = sys.platform == "win32"

if WINDOWS:  # 컴파일러가 한글 경로를 못 읽는다 → 사용자 폴더 대신 저장소 안에 설치
    for name in ("DATA", "DOWNLOADS", "USER"):
        os.environ.setdefault(f"ARDUINO_DIRECTORIES_{name}", str(ROOT / ".arduino" / name.lower()))


def fail(msg: str):
    print(f"✗ {msg}")
    sys.exit(1)


def find_cli() -> str | None:
    found = shutil.which("arduino-cli")
    if found or not WINDOWS:
        return found
    default = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Arduino CLI" / "arduino-cli.exe"
    return str(default) if default.is_file() else None


def arduino(*args: str, **kw) -> subprocess.CompletedProcess:
    exe = find_cli()
    if exe is None:
        fail("arduino-cli가 없음 → 맥: brew install arduino-cli, 윈도우: 공식 MSI 설치 후 터미널 다시 열기")
    return subprocess.run([exe, *args], cwd=ROOT, **kw)


def pico_ports() -> list[str]:
    from pico_link import pico_ports as ports
    return ports()


def uf2_drive() -> Path | None:
    """BOOTSEL 상태의 Pico 2가 드라이브로 보이면 그 경로."""
    if WINDOWS:
        roots = [Path(f"{c}:/") for c in "DEFGHIJKLMNOPQRSTUVWXYZ"]
    else:
        user = os.environ.get("USER", "")
        bases = ("/Volumes", f"/media/{user}", f"/run/media/{user}")
        roots = [p for b in bases if os.path.isdir(b) for p in Path(b).iterdir()]
    for root in roots:
        try:
            if "RP2350" in (root / "INFO_UF2.TXT").read_text(errors="replace"):
                return root
        except OSError:
            continue
    return None


def reboot_to_bootsel():
    """이미 펌웨어가 도는 Pico → 1200 bps로 열었다 닫으면 BOOTSEL 드라이브로 다시 켜진다."""
    import serial

    ports = pico_ports()
    if not ports:
        return
    try:
        with serial.Serial(ports[0], 1200) as s:
            s.dtr = False
    except serial.SerialException:
        print("  포트를 못 열었다 — 시리얼 창이 열려 있으면 닫고 같은 명령을 다시")


def flash(kind: str):
    if kind not in BUILDS:
        fail("flash 뒤에 bench · desk · ampt 중 하나")
    sketch, uf2_name, extra = BUILDS[kind]
    out = ROOT / "build" / kind
    uf2 = out / uf2_name
    uf2.unlink(missing_ok=True)  # 컴파일이 실패했을 때 옛 파일을 올리지 않게

    print("컴파일 중… (처음엔 1~2분)", flush=True)
    args = ["compile", "--fqbn", FQBN, "--output-dir", str(out), *extra, sketch]
    if WINDOWS:  # 임시 폴더도 사용자 이름(한글일 수 있음) 아래를 피한다
        args += ["--build-path", str(out / "work")]
    if arduino(*args).returncode != 0 or not uf2.is_file():
        fail("컴파일 실패 — Pico에는 아무것도 올리지 않았다")

    if uf2_drive() is None:
        reboot_to_bootsel()
    for _ in range(40):
        drive = uf2_drive()
        if drive:
            break
        time.sleep(0.5)
    else:
        fail("RP2350 드라이브가 안 보임 → USB를 뽑고, BOOTSEL 버튼을 누른 채 다시 꽂은 뒤 같은 명령")

    try:
        shutil.copyfile(uf2, drive / uf2.name)
    except OSError as e:
        if uf2_drive() is not None:  # 드라이브가 사라졌으면 다 받고 재부팅한 것
            fail(f"복사 실패: {e}")
    print(f"✓ 올림: {uf2.relative_to(ROOT)} — Pico가 스스로 다시 켜진다 ('디스크 꺼내기' 경고는 무시)")


def term():
    for _ in range(10):
        ports = pico_ports()
        if ports:
            break
        time.sleep(0.5)
    else:
        fail("Pico 포트가 없음 — USB 케이블(데이터용)과 연결 확인")
    print(f"시리얼 창: {ports[0]} — 명령 치고 Enter, 끝내기 Ctrl+]", flush=True)
    subprocess.run([sys.executable, "-m", "serial.tools.miniterm", "--eol", "LF", "--echo", ports[0], "115200"])


def setup():
    url = f"--additional-urls={BOARD_URL}"
    steps = (
        ("core", "update-index", url),
        ("core", "install", f"{CORE[0]}@{CORE[1]}", url),
        ("lib", "update-index"),
        ("lib", "install", *(f"{n}@{v}" for n, v in LIBS)),
    )
    for step in steps:
        if arduino(*step).returncode != 0:
            fail(f"실패: arduino-cli {' '.join(step[:2])} — 위 메시지 확인")
    print("✓ 설치 끝. 이어서 doctor로 확인")


def doctor():
    bad = []

    def check(good: bool, text: str, fix: str = ""):
        print(("✓ " if good else "✗ ") + text + ("" if good or not fix else f" → {fix}"))
        if not good:
            bad.append(text)

    check(sys.version_info >= (3, 10), f"Python {sys.version.split()[0]}", "3.10 이상 설치")
    for mod in ("cv2", "numpy", "serial", "pytest"):
        check(importlib.util.find_spec(mod) is not None, f"파이썬 패키지 {mod}", "pip install -r requirements.txt")
    if WINDOWS:
        check(str(ROOT).isascii(), f"저장소 경로 {ROOT}", r"C:\AmpT처럼 한글 없는 곳에 다시 clone")

    check(find_cli() is not None, "arduino-cli", "맥: brew install arduino-cli, 윈도우: 공식 MSI 설치")
    if find_cli():
        listed = arduino("core", "list", "--format", "json", capture_output=True, text=True, encoding="utf-8")
        cores = {p["id"]: p.get("installed_version") for p in json.loads(listed.stdout or "{}").get("platforms", [])}
        check(cores.get(CORE[0]) == CORE[1], f"보드 코어 {CORE[0]} {CORE[1]}", "pico setup")
        listed = arduino("lib", "list", "--format", "json", capture_output=True, text=True, encoding="utf-8")
        libs = {x["library"]["name"]: x["library"].get("version")
                for x in json.loads(listed.stdout or "{}").get("installed_libraries", [])}
        for name, ver in LIBS:
            check(libs.get(name) == ver, f"라이브러리 {name} {ver}", "pico setup")

    if importlib.util.find_spec("serial"):
        ports = pico_ports()
        print(f"· Pico 포트: {', '.join(ports) if ports else '없음 (꽂혀 있지 않으면 정상)'}")
    drive = uf2_drive()
    print(f"· BOOTSEL 드라이브: {drive if drive else '없음 (펌웨어가 돌고 있으면 정상)'}")
    print("\n모두 정상" if not bad else f"\n고칠 것 {len(bad)}개")
    sys.exit(1 if bad else 0)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "flash":
        flash(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "term":
        term()
    elif cmd == "setup":
        setup()
    elif cmd == "doctor":
        doctor()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
