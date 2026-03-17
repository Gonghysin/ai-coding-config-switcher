#!/usr/bin/env bash
set -euo pipefail

# 获取脚本所在目录（项目根目录）
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="switch_ai_config.py"

cd "$PROJECT_DIR"

if ! command -v uv >/dev/null 2>&1; then
  echo "Error: uv 未找到，请先安装 uv。" >&2
  echo "安装命令: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

uv run "$PY_SCRIPT" "$@"
