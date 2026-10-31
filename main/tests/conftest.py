import sys
from pathlib import Path

# main/ 안의 모듈을 바로 import 하게
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
