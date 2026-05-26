#!/usr/bin/env bash
set -e

if command -v python3.10 >/dev/null 2>&1; then
  PYTHON_BIN="python3.10"
else
  PYTHON_BIN="python3"
fi

"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install --upgrade -r requirements.txt
