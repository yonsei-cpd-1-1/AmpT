"""2차 발표 시연 모드 (--dual): 파단 자리와 촬영 자리가 같이 돈다.  .venv/bin/python -m pytest main/tests"""

from pathlib import Path

import cv2

import cycle
from pico_link import FakePico
from specs import BY_NAME

SAMPLES = Path(__file__).resolve().parents[2] / "vision" / "samples"


def _img(name):
    return cv2.imread(str(SAMPLES / name))


def test_dual_breaks_and_rotates(tmp_path, monkeypatch):
    monkeypatch.setattr(cycle, "LOG_DIR", tmp_path)
    link = FakePico(break_n=30.0, rot_s=0.2)
    back, front, bg = _img("2ml_back_000_01.jpg"), _img("2ml_front_000_01.jpg"), _img("bg_back_000_01.jpg")
    row = cycle.run_dual(link, back, front, True, bg, BY_NAME["5ml"])
    assert row["size"] == "5ml"                 # 파단 자리 규격은 --size
    assert row["result"] == "BROKE" and row["force_n"] == "30.0"
    assert row["cam_size"] == "2ml"             # 촬영 자리 규격은 사진으로
    assert row["cam_result"] == "ROT"
    assert (tmp_path / row["force_csv"]).exists()


def test_dual_without_photo_still_breaks(tmp_path, monkeypatch):
    """촬영 자리가 비어도 파단 쪽은 끝까지 간다."""
    monkeypatch.setattr(cycle, "LOG_DIR", tmp_path)
    bg = _img("bg_back_000_01.jpg")
    row = cycle.run_dual(FakePico(), bg, bg, True, bg, BY_NAME["1ml"])
    assert row["result"] == "BROKE"
    assert row["cam_result"] == "SKIP_SIZE"
