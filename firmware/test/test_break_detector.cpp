// 맥에서 파단 판정만 시험한다.
//   clang++ -std=c++17 firmware/test/test_break_detector.cpp -o /tmp/test_break && /tmp/test_break
#include <cstdio>
#include <cstdlib>
#include <vector>

#include "../ampt/break_detector.h"

static int failures = 0;

static void check(bool ok, const char* name) {
  printf("%s %s\n", ok ? "PASS" : "FAIL", name);
  if (!ok) failures++;
}

// 곡선을 넣고 처음 나온 판정과 그때까지의 피크를 돌려준다.
static BreakDetector::Result run(const std::vector<float>& curve, float* peak, int* at) {
  BreakDetector d(43.0f, 5.0f, 0.5f, 2);
  for (size_t i = 0; i < curve.size(); i++) {
    BreakDetector::Result r = d.update(curve[i]);
    if (r != BreakDetector::CONTINUE) {
      *peak = d.peak();
      *at = (int)i;
      return r;
    }
  }
  *peak = d.peak();
  *at = -1;
  return BreakDetector::CONTINUE;
}

int main() {
  float peak;
  int at;

  // 1. 36 N까지 오르다 뚝 떨어짐 → 파단, 파단력 36 N
  std::vector<float> broke;
  for (int i = 0; i <= 36; i++) broke.push_back((float)i);
  broke.push_back(4.0f);
  broke.push_back(1.0f);
  broke.push_back(0.5f);
  BreakDetector::Result r = run(broke, &peak, &at);
  check(r == BreakDetector::BROKE && peak == 36.0f, "파단: 36 N에서 급락");

  // 2. 안 깨지고 계속 오름 → 43 N에서 정지
  std::vector<float> strong;
  for (int i = 0; i <= 60; i++) strong.push_back((float)i);
  r = run(strong, &peak, &at);
  check(r == BreakDetector::NOBREAK && strong[at] >= 43.0f, "안 깨짐: 43 N에서 정지");

  // 3. 오르는 중 ±1 N 흔들림 → 파단으로 착각하지 않음, 그 뒤 진짜 급락은 잡음
  std::vector<float> noisy;
  srand(1);
  for (int i = 0; i <= 30; i++) noisy.push_back(i + (rand() % 201 - 100) / 100.0f);
  noisy.push_back(3.0f);
  noisy.push_back(2.0f);
  r = run(noisy, &peak, &at);
  check(r == BreakDetector::BROKE && at >= 31, "흔들림 무시 후 급락만 잡음");

  // 4. 5 N 아래 접촉 흔들림 → 아무 판정 없음
  std::vector<float> touch = {0, 2, 4, 1, 0, 3, 0.5f, 0};
  r = run(touch, &peak, &at);
  check(r == BreakDetector::CONTINUE, "작은 접촉 흔들림은 무시");

  printf(failures ? "\n%d개 실패\n" : "\n모두 통과\n", failures);
  return failures ? 1 : 0;
}
