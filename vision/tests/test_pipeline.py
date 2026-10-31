"""가짜 앰플 그림으로 파이프라인 확인.  .venv/bin/python -m pytest vision/tests"""

import cv2
import pytest

import config
from detect import analyze
from size import classify, measure, silhouette
from specs import BY_NAME
from synth import PX_PER_MM, back_image, front_image, outline

CHECK = {v: k for k, v in config.DOT_COLOR_SIZE.items()}


@pytest.mark.parametrize("name", ["1ml", "2ml", "5ml"])
def test_size_by_ratio(name):
    mask = silhouette(back_image(name))
    assert mask is not None
    result = classify(measure(mask))
    assert result.spec is not None and result.spec.name == name


@pytest.mark.parametrize("name", ["1ml", "2ml", "5ml"])
def test_size_by_mm(name):
    result = classify(measure(silhouette(back_image(name))), mm_per_px=1 / PX_PER_MM)
    assert result.spec.name == name


def test_empty_slot():
    assert silhouette(back_image(None)) is None


@pytest.mark.parametrize("name", ["1ml", "5ml"])
@pytest.mark.parametrize("angle", [0, 30, -45, 60])
def test_dot_angle(name, angle):
    r = analyze(back_image(name), front_image(name, angle))
    assert r.dot is not None
    assert r.angle == pytest.approx(angle, abs=6)


@pytest.mark.parametrize("angle", [None, 180])
def test_dot_hidden(angle):
    r = analyze(back_image("2ml"), front_image("2ml", angle))
    assert r.size.spec.name == "2ml"
    assert r.dot is None


@pytest.fixture
def whole_frame(monkeypatch):
    monkeypatch.setattr(config, "DIFF_ROI", (0, 0, 1, 1))


@pytest.mark.parametrize("name", ["1ml", "2ml", "5ml"])
def test_diff_finds_clear_ampoule(name, whole_frame):
    """배경과 밝기가 거의 같은 투명 앰플도 빈 칸 사진과 비교하면 잡힌다."""
    bg = back_image(None)
    img = bg.copy()
    cv2.fillPoly(img, [outline(name)], (222, 222, 222))
    m = measure(silhouette(img, bg))
    assert m.ratio == pytest.approx(BY_NAME[name].ratio, rel=0.05)


def test_diff_cuts_base_shadow(whole_frame):
    bg = back_image(None)
    img = bg.copy()
    cv2.ellipse(img, (300, 825), (150, 20), 0, 0, 360, (200, 200, 200), -1)
    cv2.fillPoly(img, [outline("5ml")], (40, 40, 40))
    m = measure(silhouette(img, bg))
    assert m.bottom < 830
    assert m.body_width_px == pytest.approx(16 * PX_PER_MM, rel=0.05)


def test_diff_empty_slot(whole_frame):
    assert silhouette(back_image(None), back_image(None)) is None


@pytest.mark.parametrize("color, name", [((30, 30, 220), "5ml"), ((200, 60, 30), "1ml"), ((30, 190, 230), "2ml")])
def test_dot_color_sets_size(color, name, whole_frame):
    """1 · 2 mL은 모양이 같아 점 색으로 가른다 (BGR)."""
    bg = back_image(None)
    back = bg.copy()
    cv2.fillPoly(back, [outline("1ml")], (200, 200, 200))
    front = back.copy()
    cv2.circle(front, (300, 590), 7, color, -1)
    r = analyze(back, front, bg=bg)
    assert r.dot.color == CHECK[name]
    assert r.size.spec.name == name
