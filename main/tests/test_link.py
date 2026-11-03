"""Pico 응답을 기다리는 코드 확인.  .venv/bin/python -m pytest main/tests"""

import pytest

from pico_link import FakePico, PicoError, wait_all, wait_for


def test_clamp_answers_after_vac():
    """진짜 Pico처럼 CLAMP 0 · VAC 0을 연달아 보내면 VAC가 먼저 답한다."""
    link = FakePico()
    wait_for(link, "READY")
    link.send("CLAMP 0")
    link.send("VAC 0")
    assert wait_for(link, "OK", timeout=1) == "OK VAC"
    assert wait_for(link, "OK", timeout=1) == "OK CLAMP"


@pytest.mark.parametrize("order", [("OK CLAMP", "OK VAC"), ("OK VAC", "OK CLAMP")])
def test_wait_all_takes_any_order(order):
    link = FakePico()
    link.send("CLAMP 0")
    link.send("VAC 0")
    wait_all(link, *order, timeout=1)


def test_wait_all_times_out_when_one_is_missing():
    link = FakePico()
    link.send("VAC 0")
    with pytest.raises(PicoError):
        wait_all(link, "OK CLAMP", "OK VAC", timeout=0.1)


def test_wait_for_hands_other_lines_to_on_line():
    """PUSH를 기다리는 사이 온 OK ROT를 버리지 않는다 (2차 발표 동시 진행)."""
    link = FakePico(rot_s=0.0)
    wait_for(link, "READY")
    link.send("ROT 30")
    link.send("VAC 1")
    seen = []
    assert wait_for(link, "OK VAC", timeout=1, on_line=seen.append) == "OK VAC"
    assert seen == ["OK ROT"]


def test_fake_rot_answers_later():
    link = FakePico(rot_s=0.05)
    link.send("ROT 30")
    link.send("LIFT 42")
    assert wait_for(link, "OK", timeout=1) == "OK LIFT"
    assert wait_for(link, "OK", timeout=1) == "OK ROT"
