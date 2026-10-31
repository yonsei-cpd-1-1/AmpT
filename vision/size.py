"""역광 사진 → 앰플 실루엣 → 높이 · 몸통 폭 → 규격 (1 · 2 · 5 mL).

카메라가 앰플 축을 중심으로 비스듬히(29°) 봐도 원통 실루엣은 같다.
그래서 배율을 모르면 높이 ÷ 폭 비율로, 배율(mm/px)을 알면 mm로 가른다.
"""

from dataclasses import dataclass

import cv2
import numpy as np

import config
from specs import SPECS, Spec


@dataclass
class Measure:
    top: int
    bottom: int
    height_px: int
    body_width_px: float
    axis_x: float

    @property
    def ratio(self) -> float:
        return self.height_px / self.body_width_px


@dataclass
class SizeResult:
    spec: Spec | None   # None = 모름
    best: Spec          # 가장 가까운 규격 (모름이어도)
    error: float        # 가장 가까운 규격과의 상대 오차


def touches_edge(c: np.ndarray, shape: tuple[int, int]) -> bool:
    """윤곽이 사진 가장자리에 닿나. 앰플은 화면 안에 다 들어오므로 닿으면 배경이다."""
    x, y, w, h = cv2.boundingRect(c)
    return x == 0 or y == 0 or x + w == shape[1] or y + h == shape[0]


def diff_mask(img: np.ndarray, bg: np.ndarray) -> np.ndarray:
    """빈 칸 사진과 달라진 곳 (0/255). 자동 노출로 전체가 밝아진 만큼은 먼저 뺀다."""
    k = (config.BLUR, config.BLUR)
    s = cv2.GaussianBlur(img, k, 0).astype(np.int16) - cv2.GaussianBlur(bg, k, 0).astype(np.int16)
    s -= np.median(s.reshape(-1, 3), axis=0).astype(np.int16)
    return (np.abs(s).max(axis=2) > config.DIFF_MIN).astype(np.uint8) * 255


def clean_rows(mask: np.ndarray) -> np.ndarray:
    """줄마다 왼쪽 끝 ~ 오른쪽 끝을 채우고, 몸통보다 넓어지는 바닥 그림자를 자른다."""
    rows = np.flatnonzero(mask.any(axis=1))
    spans = {int(y): row_span(mask, int(y)) for y in rows}
    widths = np.array([r - l + 1 for l, r in spans.values()])
    body = np.median(widths[len(widths) // 2:])

    out = np.zeros_like(mask)
    for i, (y, (l, r)) in enumerate(spans.items()):
        if i >= len(widths) // 2 and widths[i] > config.BASE_WIDEN_MAX * body:
            break
        out[y, l:r + 1] = 255
    return out


def diff_silhouette(img: np.ndarray, bg: np.ndarray) -> np.ndarray | None:
    """빈 칸 사진과 비교한 앰플 마스크 (0/255). 없으면 None."""
    h, w = img.shape[:2]
    x0, y0, x1, y1 = config.DIFF_ROI
    roi = np.zeros((h, w), np.uint8)
    roi[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)] = 255
    changed = cv2.bitwise_and(diff_mask(img, bg), roi)
    changed = cv2.morphologyEx(changed, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (config.DIFF_CLOSE_KERNEL, config.DIFF_CLOSE_KERNEL))
    changed = cv2.morphologyEx(changed, cv2.MORPH_CLOSE, k)

    contours, _ = cv2.findContours(changed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < config.MIN_AMPOULE_AREA_FRAC * h * w:
        return None
    mask = np.zeros((h, w), np.uint8)
    cv2.drawContours(mask, [c], -1, 255, cv2.FILLED)
    return clean_rows(mask)


def silhouette(img: np.ndarray, bg: np.ndarray | None = None) -> np.ndarray | None:
    """앰플 마스크 (0/255). 없으면 None. bg(빈 칸 사진)가 없으면 밝은 배경 앞 어두운 곳을 찾는다."""
    if bg is not None:
        return diff_silhouette(img, bg)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (config.BLUR, config.BLUR), 0)
    _, dark = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (config.CLOSE_KERNEL, config.CLOSE_KERNEL))
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, k)

    contours, _ = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if not touches_edge(c, gray.shape)]
    if not contours:
        return None
    c = max(contours, key=cv2.contourArea)
    if cv2.contourArea(c) < config.MIN_AMPOULE_AREA_FRAC * img.shape[0] * img.shape[1]:
        return None
    mask = np.zeros(gray.shape, np.uint8)
    cv2.drawContours(mask, [c], -1, 255, cv2.FILLED)
    return mask


def row_span(mask: np.ndarray, y: int) -> tuple[int, int] | None:
    """y 행에서 앰플의 왼쪽 · 오른쪽 끝 x."""
    xs = np.flatnonzero(mask[y])
    if xs.size == 0:
        return None
    return int(xs[0]), int(xs[-1])


def measure(mask: np.ndarray) -> Measure:
    rows = np.flatnonzero(mask.any(axis=1))
    top, bottom = int(rows[0]), int(rows[-1])
    h = bottom - top + 1

    lo, hi = config.BODY_ROWS
    widths, centers = [], []
    for y in range(int(bottom - hi * h), int(bottom - lo * h) + 1):
        span = row_span(mask, y)
        if span:
            widths.append(span[1] - span[0] + 1)
            centers.append((span[0] + span[1]) / 2)
    return Measure(top, bottom, h, float(np.median(widths)), float(np.median(centers)))


def classify(m: Measure, mm_per_px: float | None = None) -> SizeResult:
    def error(s: Spec) -> float:
        if mm_per_px:
            dh = (m.height_px * mm_per_px - s.height) / s.height
            dw = (m.body_width_px * mm_per_px - s.body_d) / s.body_d
            return float(np.hypot(dh, dw))
        return abs(m.ratio - s.ratio) / s.ratio

    best = min(SPECS, key=error)
    err = error(best)
    return SizeResult(best if err <= config.MAX_CLASS_ERROR else None, best, err)
