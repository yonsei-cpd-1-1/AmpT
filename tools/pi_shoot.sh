#!/usr/bin/env bash
# Pi 카메라로 역광 · 정면광 한 쌍 찍기 (Pi에서 실행). 이름은 vision/detect.py 규칙을 따른다.
#   bash ~/AmpT/tools/pi_shoot.sh 5ml_000      # {규격}_{점방향} → ~/samples/5ml_back_000_01.jpg + 5ml_front_000_01.jpg
#   bash ~/AmpT/tools/pi_shoot.sh test         # 한 장만 찍어 초점 · 구도 확인 → ~/samples/test.jpg
# 카메라와 앰플은 그대로 두고 조명만 바꾼다. 맥으로 가져오기: rsync -av ampt@ampt.local:samples/ vision/samples/
set -euo pipefail
OUT=~/samples
LENS=${LENS:-6.25}  # 초점 고정 (디옵터 = 1 ÷ 거리 m, 16 cm). 자동 초점은 역광 사진에서 흐려진다
mkdir -p "$OUT"

shoot() {  # 크기는 2304 × 1296 (Camera Module 3 2×2 비닝)
  rpicam-still -n -t 1500 --autofocus-mode manual --lens-position "$LENS" --width 2304 --height 1296 -o "$1" 2>/dev/null
  echo "  ✓ $1"
}

prefix=${1:?"예: bash pi_shoot.sh 5ml_000  (규격_점방향)"}
if [ "$prefix" = test ]; then
  shoot "$OUT/test.jpg"
  exit 0
fi

size=${prefix%_*}
angle=${prefix#*_}
n=1
while [ -e "$OUT/${size}_back_${angle}_$(printf %02d $n).jpg" ]; do n=$((n + 1)); done
num=$(printf %02d $n)

read -r -p "① 역광: 앰플 뒤에 흰 종이 + 종이 뒤에서 빛 → Enter "
shoot "$OUT/${size}_back_${angle}_${num}.jpg"
read -r -p "② 정면광: 같은 빛을 카메라 옆에서 앰플 쪽으로 → Enter "
shoot "$OUT/${size}_front_${angle}_${num}.jpg"
