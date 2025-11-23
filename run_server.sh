#!/bin/bash

# 切换到脚本所在目录
cd "$(dirname "$0")"
echo "当前目录: $(pwd)"

. .venv/bin/activate
uv run -m src.main
