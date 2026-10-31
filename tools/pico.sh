#!/usr/bin/env bash
# 맥: tools/pico.sh flash bench · term · doctor · setup (내용은 tools/pico.py, 윈도우는 tools\pico)
exec "$(dirname "$0")/../.venv/bin/python" "$(dirname "$0")/pico.py" "$@"
