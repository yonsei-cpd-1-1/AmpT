// 파단 판정 — 아두이노에 의존하지 않는 순수 C++ (맥에서 시험: firmware/test).
// 힘이 minPeak을 넘은 뒤, 피크의 (1 - dropRatio) 아래로 confirm 샘플 연속 떨어지면 파단.
// stopN에 닿으면 안 깨진 것으로 보고 멈춘다 (낙하쪽 조 보호).
#pragma once

class BreakDetector {
 public:
  enum Result { CONTINUE, BROKE, NOBREAK };

  BreakDetector(float stopN, float minPeakN, float dropRatio, int confirmSamples)
      : stopN_(stopN), minPeakN_(minPeakN), dropRatio_(dropRatio),
        confirm_(confirmSamples) {
    reset();
  }

  void reset() {
    peak_ = 0;
    below_ = 0;
  }

  Result update(float forceN) {
    if (forceN >= stopN_) return NOBREAK;
    if (forceN > peak_) peak_ = forceN;
    if (peak_ >= minPeakN_ && forceN < peak_ * (1 - dropRatio_)) {
      if (++below_ >= confirm_) return BROKE;
    } else {
      below_ = 0;
    }
    return CONTINUE;
  }

  float peak() const { return peak_; }

 private:
  float stopN_, minPeakN_, dropRatio_;
  int confirm_;
  float peak_;
  int below_;
};
