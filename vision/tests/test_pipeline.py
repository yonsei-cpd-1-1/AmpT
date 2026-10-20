"""가짜 앰플 그림으로 파이프라인 확인.  .venv/bin/python -m pytest vision/tests"""

import pytest

from detect import analyze
from size import classify, measure, silhouette
from synth import PX_PER_MM, back_image, front_image


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
