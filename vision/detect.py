"""사진 폴더 → 사진마다 규격 · 점 · 각도 표.

    python vision/detect.py vision/samples/
    python vision/detect.py vision/samples/ --calib vision/calib.npz --debug vision/samples/debug

파일 이름 규칙: {규격}_{조명}_{점방향}_{번호}.jpg  예) 5ml_back_000_01.jpg, 5ml_front_000_01.jpg
- 같은 규격 · 점방향 · 번호의 back(역광)과 front(정면광)를 한 쌍으로 본다 (아이폰은 움직이지 않고 조명만 바꿔 찍기)
- back에서 실루엣 · 규격, front에서 점 · 각도
- 이름에서 정답을 읽어 맞았는지 같이 표시한다. 규칙에 안 맞는 사진은 한 장으로 둘 다 해 본다
"""

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from calib import load_calib, undistort
from dot import Dot, dot_angle, find_dot
import config
from size import Measure, SizeResult, classify, measure, silhouette
from specs import BY_NAME

NAME_RE = re.compile(r"^(\d+ml)_(back|front)_(\d{3})_(\d+)$", re.IGNORECASE)
IMAGE_EXT = {".jpg", ".jpeg", ".png"}


@dataclass
class Result:
    mask: np.ndarray | None = None
    meas: Measure | None = None
    size: SizeResult | None = None
    dot: Dot | None = None
    angle: float | None = None


def analyze(back: np.ndarray, front: np.ndarray, mm_per_px: float | None = None,
            bg: np.ndarray | None = None) -> Result:
    r = Result()
    r.mask = silhouette(back, bg)
    if r.mask is None:
        return r
    r.meas = measure(r.mask)
    r.size = classify(r.meas, mm_per_px)
    r.dot = find_dot(front, r.mask, r.meas, r.size.best)
    if r.dot is not None:
        r.angle = dot_angle(r.dot, r.mask)
    if bg is not None:  # 실물은 모양보다 점 색이 규격을 정한다 → 점이 없으면 규격도 모름
        spec = BY_NAME[config.DOT_COLOR_SIZE[r.dot.color]] if r.dot else None
        r.size = SizeResult(spec, spec or r.size.best, r.size.error)
    return r


def draw(img: np.ndarray, r: Result) -> np.ndarray:
    out = img.copy()
    if r.mask is not None:
        contours, _ = cv2.findContours(r.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(out, contours, -1, (255, 160, 0), 2)
    if r.meas is not None:
        x = int(r.meas.axis_x)
        cv2.line(out, (x, r.meas.top), (x, r.meas.bottom), (255, 160, 0), 1)
    if r.dot is not None:
        cv2.circle(out, (int(r.dot.x), int(r.dot.y)), 12, (0, 255, 0), 2)
    # putText는 한글을 못 그려서 영어로
    label = "empty" if r.size is None else (r.size.spec.name if r.size.spec else f"? ({r.size.best.name})")
    if r.size is not None:
        label += "  dot " + (f"{r.angle:+.0f}deg" if r.angle is not None else "none")
    cv2.putText(out, label, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 255), 3)
    return out


def collect(folder: Path) -> list[tuple[str, Path, Path, dict]]:
    """(이름, back 경로, front 경로, 정답) 목록."""
    pairs: dict[tuple, dict] = {}
    singles = []
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() not in IMAGE_EXT:
            continue
        mt = NAME_RE.match(p.stem)
        if not mt:
            singles.append((p.stem, p, p, {}))
            continue
        size, light, angle, n = mt.groups()
        key = (size.lower(), angle, n)
        pairs.setdefault(key, {})[light.lower()] = p

    items = []
    for (size, angle, n), d in pairs.items():
        back = d.get("back") or d.get("front")
        front = d.get("front") or d.get("back")
        items.append((f"{size}_{angle}_{n}", back, front, {"size": size, "angle": int(angle)}))
    return items + singles


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--calib", help="calib.py로 만든 .npz")
    ap.add_argument("--mm-per-px", type=float, help="배율을 알면 mm로 판별 (모르면 높이÷폭 비율)")
    ap.add_argument("--bg", type=Path, help="앰플 없는 빈 칸 사진 (실물은 이것과 비교해 윤곽을 찾는다)")
    ap.add_argument("--debug", type=Path, help="결과를 그린 사진을 저장할 폴더")
    args = ap.parse_args()

    calib = load_calib(args.calib)
    bg = None
    if args.bg:
        bg = cv2.imread(str(args.bg))
        if bg is None:
            raise SystemExit(f"빈 칸 사진을 못 읽었다: {args.bg}")
        bg = undistort(bg, calib)
    if args.debug:
        args.debug.mkdir(parents=True, exist_ok=True)

    size_ok = size_n = 0
    dot_ok = dot_n = 0
    angle_errs = []

    print(f"{'사진':<16} {'규격':>6} {'판별':>8} {'오차':>6} {'비율':>6}  {'점':<4} {'정답각':>6} {'측정각':>6}")
    for name, bp, fp, truth in collect(args.folder):
        if name.startswith("bg_"):
            continue
        back = undistort(cv2.imread(str(bp)), calib)
        front = undistort(cv2.imread(str(fp)), calib)
        r = analyze(back, front, args.mm_per_px, bg)

        if r.size is None:
            print(f"{name:<16} {truth.get('size', '-'):>6} {'빈 칸':>8}")
            continue

        guess = r.size.spec.name if r.size.spec else "모름"
        t_size = truth.get("size")
        if t_size and truth.get("angle") != 90:  # 90°는 점이 옆으로 숨어 규격도 다시 봐야 한다
            size_n += 1
            size_ok += guess == t_size
            guess += " ✓" if guess == t_size else " ✗"

        # 유리가 비쳐 뒤쪽 점도 보인다: 180°도 0°처럼 나온다. 90°는 경계라 셈에서 뺀다
        t_angle = truth.get("angle")
        seen = r.dot is not None
        mark = "있음" if seen else "없음"
        if t_angle is not None and t_angle != 90:
            dot_n += 1
            dot_ok += seen
            mark += "✓" if seen else "✗"
            if seen and t_angle < 90 and r.angle is not None:
                angle_errs.append(abs(abs(r.angle) - t_angle))  # 부호(좌우)는 아직 모름 → 크기만 비교

        ang = f"{r.angle:+.1f}" if r.angle is not None else "-"
        print(f"{name:<16} {t_size or '-':>6} {guess:>8} {r.size.error:>6.1%} {r.meas.ratio:>6.2f}  "
              f"{mark:<4} {t_angle if t_angle is not None else '-':>6} {ang:>6}")

        if args.debug:
            cv2.imwrite(str(args.debug / f"{name}.jpg"), draw(front, r))

    print()
    if size_n:
        print(f"규격 판별: {size_ok}/{size_n}")
    if dot_n:
        print(f"점 있음/없음: {dot_ok}/{dot_n}")
    if angle_errs:
        print(f"각도 오차(크기): 평균 {np.mean(angle_errs):.1f}°, 최대 {np.max(angle_errs):.1f}° ({len(angle_errs)}장)")


if __name__ == "__main__":
    main()
