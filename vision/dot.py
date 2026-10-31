"""사진 → 머리 쪽 OPC 점 (빨강 · 노랑 · 파랑) → 점 각도.

점이 원통 표면에 있으므로 축에서 가로로 떨어진 거리 dx = r · sin θ → θ = asin(dx / r).
θ = 0 이면 점이 카메라를 정면으로 본다. + 는 사진에서 축 오른쪽.
유리가 비쳐서 뒤쪽 점(θ = 180°)도 정면 점처럼 보인다 → 사진 한 장으로는 앞뒤를 못 가른다.
"""

import math
from dataclasses import dataclass

import cv2
import numpy as np

import config
from size import Measure, row_span
from specs import Spec


@dataclass
class Dot:
    x: float
    y: float
    area: float
    color: str


def color_mask(hsv: np.ndarray, color: str) -> np.ndarray:
    s, v = config.DOT_S_MIN, config.DOT_V_MIN
    m = np.zeros(hsv.shape[:2], np.uint8)
    for lo, hi in config.DOT_COLORS[color]:
        m = cv2.bitwise_or(m, cv2.inRange(hsv, (lo, s, v), (hi, 255, 255)))
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


def head_roi(mask: np.ndarray, m: Measure, spec: Spec) -> tuple[int, int, int, int]:
    """점을 찾을 사각형 (x0, y0, x1, y1): 머리 끝 ~ 노치 조금 아래, 앰플 폭 + 여유."""
    notch_y = m.bottom - spec.notch_h / spec.height * m.height_px
    y1 = int(notch_y + config.HEAD_MARGIN_FRAC * m.height_px)
    cols = np.flatnonzero(mask[m.top:y1].any(axis=0))
    pad = int(0.1 * m.body_width_px)
    return max(cols[0] - pad, 0), m.top, min(cols[-1] + pad, mask.shape[1] - 1), y1


def find_dot(img: np.ndarray, mask: np.ndarray | None = None,
             m: Measure | None = None, spec: Spec | None = None) -> Dot | None:
    """색 점 하나. 실루엣 · 규격을 주면 머리 영역만 본다 (HSV 변환이 비싸서)."""
    x0, y0 = 0, 0
    crop = img
    tinted = False
    if mask is not None and m is not None and spec is not None:
        x0, y0, x1, y1 = head_roi(mask, m, spec)
        crop = img[y0:y1, x0:x1]
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    if crop is not img:
        tinted = np.median(hsv[..., 1][mask[y0:y1, x0:x1] > 0]) > config.TINTED_GLASS_S_MIN
    max_area = config.DOT_MAX_AREA_FRAC * (cv2.countNonZero(mask) if mask is not None else img.size / 3)

    best = None
    for color in config.DOT_COLORS:
        if tinted and color == "yellow":
            continue
        contours, _ = cv2.findContours(color_mask(hsv, color), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area = cv2.contourArea(c)
            if not config.DOT_MIN_AREA_PX <= area <= max_area:
                continue
            perim = cv2.arcLength(c, True)
            if perim == 0 or 4 * math.pi * area / perim**2 < config.DOT_MIN_CIRCULARITY:
                continue
            _, _, w, h = cv2.boundingRect(c)
            if w > config.DOT_MAX_WIDE * h:
                continue
            if best is None or area > best[1]:
                best = (c, area, color)
    if best is None:
        return None

    mo = cv2.moments(best[0])
    return Dot(x0 + mo["m10"] / mo["m00"], y0 + mo["m01"] / mo["m00"], best[1], best[2])


def dot_angle(dot: Dot, mask: np.ndarray) -> float | None:
    """점 높이에서의 앰플 폭으로 반지름 r, 가운데 축 → θ (°)."""
    span = row_span(mask, int(round(dot.y)))
    if span is None:
        return None
    r = (span[1] - span[0]) / 2
    cx = (span[0] + span[1]) / 2
    if r <= 0:
        return None
    return math.degrees(math.asin(max(-1.0, min(1.0, (dot.x - cx) / r))))
