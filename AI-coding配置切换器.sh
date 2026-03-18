#!/usr/bin/env bash
set -euo pipefail

# 获取脚本所在目录（项目根目录）
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$PROJECT_DIR"

if ! command -v uv >/dev/null 2>&1; then
  echo "Error: uv 未找到，请先安装 uv。" >&2
  echo "安装命令: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

# 管理CLI的命令
MANAGE_COMMANDS="add-provider|remove-provider|add-model|remove-model|set-config|get-config|edit-provider|edit-models|init|list"

# 判断是管理命令还是切换配置
if [[ $# -gt 0 && "$1" =~ ^($MANAGE_COMMANDS)$ ]]; then
  # 执行管理CLI
  uv run python ai-config-cli.py "$@"
else
  # 执行配置切换
  uv run python switch_ai_config.py "$@"
fi
