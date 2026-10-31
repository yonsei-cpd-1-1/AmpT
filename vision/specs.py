"""앰플 치수 (mm, 바닥 기준). 10/8에 산 앰플을 자로 잰 값 (윤정호 10/10).
10/31 카메라 측정과 달라 자로 다시 잰 뒤 고친다. notch_h가 그대로 LIFT 값이 된다."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Spec:
    name: str
    body_d: float     # 몸통 지름
    height: float     # 전체 높이
    notch_h: float    # 노치(목) 높이 → Pico LIFT 값
    notch_d: float

    @property
    def ratio(self) -> float:
        """높이 ÷ 몸통 폭. 사진 배율을 몰라도 규격을 가를 수 있다."""
        return self.height / self.body_d


# 2차 발표 시제품 대상: 1 · 2 · 5 mL
SPECS = [
    Spec("1ml", body_d=10.0, height=50.0, notch_h=27.0, notch_d=6.0),
    Spec("2ml", body_d=10.0, height=60.0, notch_h=36.0, notch_d=6.0),
    Spec("5ml", body_d=16.0, height=72.0, notch_h=42.0, notch_d=7.0),
]

BY_NAME = {s.name: s for s in SPECS}
