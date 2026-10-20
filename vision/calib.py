"""체커보드 사진으로 렌즈 왜곡 보정값을 만든다 (광각 Wide · 아이폰 0.5×).

    python vision/calib.py vision/samples/calib_*.jpg -o vision/calib.npz

체커보드는 안쪽 모서리 9 × 6 (OpenCV 기본 패턴). 같은 카메라 · 같은 해상도에서만 쓴다.
"""

import argparse
import sys

import cv2
import numpy as np

PATTERN = (9, 6)


def calibrate(paths: list[str]) -> tuple[np.ndarray, np.ndarray, float]:
    objp = np.zeros((PATTERN[0] * PATTERN[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:PATTERN[0], 0:PATTERN[1]].T.reshape(-1, 2)

    obj_pts, img_pts, size = [], [], None
    for p in paths:
        gray = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            print(f"  읽기 실패: {p}")
            continue
        found, corners = cv2.findChessboardCorners(gray, PATTERN)
        print(f"  {'찾음' if found else '못 찾음'}: {p}")
        if not found:
            continue
        corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1),
                                   (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001))
        obj_pts.append(objp)
        img_pts.append(corners)
        size = gray.shape[::-1]

    if len(obj_pts) < 5:
        sys.exit(f"체커보드를 찾은 사진이 {len(obj_pts)}장 — 5장 이상 필요")
    rms, K, dist, _, _ = cv2.calibrateCamera(obj_pts, img_pts, size, None, None)
    return K, dist, rms


def load_calib(path: str | None):
    if not path:
        return None
    d = np.load(path)
    return d["K"], d["dist"]


def undistort(img: np.ndarray, calib) -> np.ndarray:
    if calib is None:
        return img
    K, dist = calib
    return cv2.undistort(img, K, dist)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("-o", "--out", default="vision/calib.npz")
    args = ap.parse_args()

    K, dist, rms = calibrate(args.images)
    np.savez(args.out, K=K, dist=dist)
    print(f"저장: {args.out}  (재투영 오차 {rms:.2f} px — 1 px 아래면 양호)")
