"""맥 카메라(내장 웹캠 · 아이폰 연속성 카메라)로 미리보기 + 판별 결과를 겹쳐 보고, 키로 사진을 저장한다.

    python vision/live.py --list                      # 카메라 번호 찾기
    python vision/live.py --camera 1 --prefix 5ml_000 # b: 역광 저장, f: 정면광 저장, q: 끝

저장 이름은 detect.py 규칙을 따른다: 5ml_back_000_01.jpg, 5ml_front_000_01.jpg
처음 실행하면 macOS가 카메라 권한을 묻는다 (터미널 / VS Code에 허용).
"""

import argparse
from pathlib import Path

import cv2

from detect import analyze, draw


def list_cameras():
    for i in range(5):
        cap = cv2.VideoCapture(i)
        ok, frame = cap.read()
        if ok:
            print(f"카메라 {i}: {frame.shape[1]} × {frame.shape[0]}")
        cap.release()


def next_number(out: Path, size: str, angle: str) -> int:
    n = 1
    while (out / f"{size}_back_{angle}_{n:02d}.jpg").exists() or (out / f"{size}_front_{angle}_{n:02d}.jpg").exists():
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--prefix", default="5ml_000", help="{규격}_{점방향}, 예: 2ml_090")
    ap.add_argument("--out", type=Path, default=Path("vision/samples"))
    args = ap.parse_args()

    if args.list:
        list_cameras()
        return

    size, angle = args.prefix.split("_")
    args.out.mkdir(parents=True, exist_ok=True)
    n = next_number(args.out, size, angle)
    saved = set()

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        raise SystemExit(f"카메라 {args.camera}를 못 열었다 — --list로 번호 확인")

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        view = draw(frame, analyze(frame, frame))
        cv2.putText(view, f"{size}_{angle}_{n:02d}  [b]back [f]front [q]quit", (20, view.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.imshow("AmpT live", view)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key in (ord("b"), ord("f")):
            light = "back" if key == ord("b") else "front"
            path = args.out / f"{size}_{light}_{angle}_{n:02d}.jpg"
            cv2.imwrite(str(path), frame)
            print(f"저장: {path}")
            saved.add(light)
            if saved == {"back", "front"}:  # 한 쌍 다 찍으면 다음 번호
                n += 1
                saved.clear()

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
