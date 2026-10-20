"""정면광 사진 → 머리 쪽 빨간 OPC 점 → 점 각도.

점이 원통 표면에 있으므로 축에서 가로로 떨어진 거리 dx = r · sin θ → θ = asin(dx / r).
θ = 0 이면 점이 카메라를 정면으로 본다. + 는 사진에서 축 오른쪽.
점이 뒤쪽(|θ| > 90°)에 있으면 안 보인다 → None → 180° 돌려 다시 찍는다.
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


def red_mask(img: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    s, v = config.RED_S_MIN, config.RED_V_MIN
    low = cv2.inRange(hsv, (0, s, v), (config.RED_H_LOW_MAX, 255, 255))
    high = cv2.inRange(hsv, (config.RED_H_HIGH_MIN, s, v), (180, 255, 255))
    m = cv2.bitwise_or(low, high)
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
    """빨간 점 하나. 실루엣 · 규격을 주면 머리 영역만 본다 (HSV 변환이 비싸서)."""
    x0, y0 = 0, 0
    crop = img
    if mask is not None and m is not None and spec is not None:
        x0, y0, x1, y1 = head_roi(mask, m, spec)
        crop = img[y0:y1, x0:x1]

    red = red_mask(crop)
    contours, _ = cv2.findContours(red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    max_area = config.DOT_MAX_AREA_FRAC * (cv2.countNonZero(mask) if mask is not None else img.size / 3)

    best = None
    for c in contours:
        area = cv2.contourArea(c)
        if not config.DOT_MIN_AREA_PX <= area <= max_area:
            continue
        perim = cv2.arcLength(c, True)
        if perim == 0 or 4 * math.pi * area / perim**2 < config.DOT_MIN_CIRCULARITY:
            continue
        if best is None or area > best[1]:
            best = (c, area)
    if best is None:
        return None

    mo = cv2.moments(best[0])
    return Dot(x0 + mo["m10"] / mo["m00"], y0 + mo["m01"] / mo["m00"], best[1])


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
