"""코드로 그린 가짜 앰플 사진 — 파이프라인이 돌아가는지만 본다 (실물 성능과 무관)."""

import math

import cv2
import numpy as np

from specs import BY_NAME

PX_PER_MM = 8
W, H = 600, 900
BODY_END = {"1ml": 23.0, "2ml": 32.0, "5ml": 37.0}  # 몸통 끝(어깨 시작), 04 §3-1


def outline(name: str, cx: float = W / 2, base: float = H - 80) -> np.ndarray:
    """옆에서 본 앰플 윤곽 (다각형)."""
    s = BY_NAME[name]
    k = PX_PER_MM
    head_d = s.notch_d * 1.4
    right = [  # (반지름 mm, 바닥에서 높이 mm) — 아래에서 위로
        (s.body_d / 2, 0),
        (s.body_d / 2, BODY_END[name]),
        (s.notch_d / 2, s.notch_h),
        (head_d / 2, s.notch_h + 4),
        (head_d / 2, s.height - 3),
        (head_d / 4, s.height),
    ]
    pts = [(cx + r * k, base - z * k) for r, z in right]
    pts += [(cx - r * k, base - z * k) for r, z in reversed(right)]
    return np.array(pts, np.int32)


def back_image(name: str | None) -> np.ndarray:
    img = np.full((H, W, 3), 235, np.uint8)
    if name:
        cv2.fillPoly(img, [outline(name)], (40, 40, 40))
    return img


def front_image(name: str, angle_deg: float | None) -> np.ndarray:
    """정면광: 밝은 앰플 + 머리 쪽 빨간 점. angle_deg=None 또는 |각| ≥ 90 이면 점 안 보임."""
    img = np.full((H, W, 3), 235, np.uint8)
    poly = outline(name)
    cv2.fillPoly(img, [poly], (200, 200, 200))
    if angle_deg is None or abs(angle_deg) >= 90:
        return img

    s = BY_NAME[name]
    y = int(H - 80 - (s.notch_h + 2.5) * PX_PER_MM)  # 노치 바로 위
    mask = np.zeros((H, W), np.uint8)
    cv2.fillPoly(mask, [poly], 255)
    xs = np.flatnonzero(mask[y])
    cx, r = (xs[0] + xs[-1]) / 2, (xs[-1] - xs[0]) / 2
    x = cx + r * math.sin(math.radians(angle_deg))
    dot_r = 0.8 * PX_PER_MM
    axes = (max(int(dot_r * math.cos(math.radians(angle_deg))), 2), int(dot_r))
    cv2.ellipse(img, (int(x), y), axes, 0, 0, 360, (30, 30, 220), -1)
    return img
