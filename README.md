# AI Coding 配置切换器

一个用于快速切换不同 AI Coding 工具配置的命令行工具，支持 Claude Code、OpenCode、Codex。

## 功能特性

- 🔄 快速切换不同的 AI 配置文件
- 💾 自动备份当前配置
- 🎯 支持多种 AI Coding 工具
- 🖥️ 交互式菜单选择
- 🔍 Dry-run 模式预览操作
- 📦 两级目录结构（提供商 -> 模型）
- 🛠️ 完整的 CLI 管理工具

## 支持的工具

- **Claude Code** - Anthropic 官方 CLI 工具
- **OpenCode** - 开源 AI 编码 CLI 工具
- **Codex** - OpenAI Codex CLI

## 项目目录结构

```
ai-coding-config-switcher/
├── .gitignore                   # Git 忽略规则
├── .python-version              # Python 版本配置
├── README.md                    # 项目说明文档
├── pyproject.toml               # UV 项目配置和依赖
├── uv.lock                      # UV 依赖锁定文件
├── main.py                      # 程序入口文件
├── switch_ai_config.py          # 配置切换模块
├── ai-config-cli.py             # 管理CLI工具
├── AI-coding配置切换器.sh       # Shell 快捷脚本
└── configs/                     # 配置文件目录
    ├── config/                  # 配置切换器本身的配置
    │   └── paths.json.template  # 路径配置模板
    └── claude_code/             # Claude Code 配置
        ├── {provider}/           # 提供商目录
        │   ├── config.json       # 提供商配置（API URL、Key、模型列表）
        │   └── settings.json.bak # 自动备份
        ├── minimax/              # 示例：Minimax 提供商
        │   └── config.json
        └── openai/              # 示例：OpenAI 提供商（可选）
            └── config.json
```

## 安装配置

### 1. 克隆项目

```bash
git clone https://github.com/Gonghysin/ai-coding-config-switcher.git
cd ai-coding-config-switcher
```

### 2. 配置 UV 环境

本项目使用 [uv](https://github.com/astral-sh/uv) 作为 Python 包管理器。

#### 安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 Homebrew
brew install uv
```

#### 创建虚拟环境并安装依赖

```bash
# uv 会自动创建虚拟环境并安装依赖
uv sync
```

### 3. 设置 Shell 脚本（可选）

```bash
chmod +x AI-coding配置切换器.sh
```

## 管理命令

本工具提供 `ai-config-cli.py` 用于管理提供商和模型配置。
目前 `ai-config-cli.py` 主要管理 `configs/claude_code` 目录；`codex` / `opencode` 建议使用 `switch_ai_config.py` 的交互式管理流程。

### 添加提供商

```bash
# 方式1: 一步到位（添加提供商并设置配置）
uv run python ai-config-cli.py init <provider_name> \
  --api-url "https://api.example.com/anthropic" \
  --api-key "sk-xxx" \
  --model "model-name:别名" \
  --model "model-name2:别名2"

# 方式2: 分别添加
uv run python ai-config-cli.py add-provider <provider_name> --api-url "..." --api-key "..."
```

### 列出提供商

```bash
uv run python ai-config-cli.py list
```

### 设置/更新提供商配置

```bash
# 更新 API Key
uv run python ai-config-cli.py set-config <provider_name> --api-key "sk-new-key"

# 更新 API URL
uv run python ai-config-cli.py set-config <provider_name> --api-url "https://new-api.example.com"

# 同时更新
uv run python ai-config-cli.py set-config <provider_name> --api-url "..." --api-key "..."
```

### 查看提供商配置

```bash
uv run python ai-config-cli.py get-config <provider_name>
```

### 添加模型

```bash
# 添加模型
uv run python ai-config-cli.py add-model <provider_name> <model_name> --alias <别名>

# 示例
uv run python ai-config-cli.py add-model minimax MiniMax-M2.7-highspeed --alias "M2.7极速版"
```

### 列出模型

```bash
uv run python ai-config-cli.py list-models <provider_name>
```

### 删除模型

```bash
uv run python ai-config-cli.py remove-model <provider_name> <model_name>
```

### 删除提供商

```bash
uv run python ai-config-cli.py remove-provider <provider_name>
```

## 使用方法

### 基本用法

```bash
# 交互式选择提供商和模型
uv run python switch_ai_config.py

# 或使用 shell 脚本
./AI-coding配置切换器.sh
```

### 命令行参数

```bash
# 列出所有提供商
uv run python switch_ai_config.py --list-providers

# 列出提供商下的模型
uv run python switch_ai_config.py --list-models minimax

# 指定提供商和模型切换
uv run python switch_ai_config.py -p minimax -m MiniMax-M2.5-highspeed

# Dry-run 模式（仅预览，不实际执行）
uv run python switch_ai_config.py -p minimax -m MiniMax-M2.5-highspeed --dry-run
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `-t, --tool` | 工具名称：`claude code` / `opencode` / `codex` |
| `-p, --provider` | AI 服务提供商名称 |
| `-m, --model` | 模型名称 |
| `--list-providers` | 列出所有可用的提供商 |
| `--list-models <name>` | 列出指定提供商下的所有模型 |
| `--dry-run` | 只展示操作，不写入文件 |

## Codex 说明

- Codex 当前用户级主配置文件是 `~/.codex/config.toml`
- Codex 当前也支持项目级配置文件 `.codex/config.toml`，项目级优先于系统级
- 使用 OpenAI API Key 登录时，认证信息存放在 `~/.codex/auth.json`
- 本项目中的 `configs/codex/<provider>/config.json` 是“提供商模板”，不是 Codex 的真实目标配置文件
- Codex 提供商配置支持 `auth_mode`
- `openai`：切换时写入所选 scope 的 `config.toml`，并把选中的 OpenAI API Key 同步到 `~/.codex/auth.json`
- `bearer_token`：切换时写入所选 scope 的 `config.toml` 的 `experimental_bearer_token`，适合第三方 provider 自有 token
- 如果 `auth_mode = "openai"` 且 provider 配置里未保存 API Key，切换器会保留现有 `~/.codex/auth.json` 登录态不变
- 选择 Codex 项目级配置时，写入目标是当前目录下的 `.codex/config.toml`
- 注意：即使选择项目级配置，`auth.json` 仍然是用户级文件 `~/.codex/auth.json`

## 完整示例：添加 MiniMax 提供商

```bash
# 1. 初始化提供商
uv run python ai-config-cli.py init minimax \
  --api-url "https://api.minimaxi.com/anthropic" \
  --api-key "sk-your-api-key"

# 2. 添加模型
uv run python ai-config-cli.py add-model minimax "MiniMax-M2.7" --alias "M2.7标准版"
uv run python ai-config-cli.py add-model minimax "MiniMax-M2.7-highspeed" --alias "M2.7极速版"
uv run python ai-config-cli.py add-model minimax "MiniMax-M2.5" --alias "M2.5标准版"
uv run python ai-config-cli.py add-model minimax "MiniMax-M2.5-highspeed" --alias "M2.5极速版"

# 3. 列出添加的模型
uv run python ai-config-cli.py list-models minimax

# 4. 切换配置
uv run python switch_ai_config.py -p minimax -m MiniMax-M2.5-highspeed
```

## 注意事项

- ⚠️ 配置文件可能包含敏感信息（API Key），请勿提交到公开仓库
- ✅ 使用 `.gitignore` 已自动排除实际配置文件
- ✅ 只有 `.template` 文件会被提交到 git
- 💡 为不同的 API 提供商创建不同的目录，统一切换体验

## 常见问题

### Q: 提供商配置文件在哪里？

A: 每个提供商的配置位于 `configs/{tool}/{provider_name}/config.json`。其中 Codex 的真实目标文件是 `~/.codex/config.toml`，认证文件是 `~/.codex/auth.json`。

### Q: Codex 的项目级配置文件在哪里？

A: 位于当前目录下的 `.codex/config.toml`。当它存在时，会优先于系统级 `~/.codex/config.toml` 生效。

### Q: 如何查看所有提供商？

A: 使用 `uv run python ai-config-cli.py list` 或 `uv run python switch_ai_config.py --list-providers`

### Q: 如何恢复之前的配置？

A: 备份文件保存在 `configs/{tool}/{provider}/settings.{scope}.bak`。Codex 在 `openai` 模式下还会额外备份 `configs/codex/{provider}/auth.{scope}.bak`。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
