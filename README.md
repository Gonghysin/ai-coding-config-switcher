# AI Coding 配置切换器

一个用于快速切换不同 AI Coding 工具配置的命令行工具，支持 Claude Code 等多种工具。

## 功能特性

- 🔄 快速切换不同的 AI 配置文件
- 💾 自动备份当前配置
- 🎯 支持多种 AI Coding 工具
- 🖥️ 交互式菜单选择
- 🔍 Dry-run 模式预览操作

## 支持的工具

- **Claude Code** - Anthropic 官方 CLI 工具
- **Codex** - OpenAI Codex（计划支持）

## 安装配置

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd AIcoding配置切换器
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

### 3. 配置路径

#### 找到 Claude Code 配置文件位置

Claude Code 的配置文件默认位于：

- **macOS/Linux**: `~/.claude/settings.json`
- **Windows**: `%USERPROFILE%\.claude\settings.json`

你可以通过以下命令确认：

```bash
# macOS/Linux
ls -la ~/.claude/settings.json

# Windows
dir %USERPROFILE%\.claude\settings.json
```

#### 配置本工具的路径

1. 复制配置模板：

```bash
cp config/paths.json.template config/paths.json
```

2. 编辑 `config/paths.json`，填入你的实际路径：

```json
{
  "claude_code": {
    "target_file": "/Users/YOUR_USERNAME/.claude/settings.json",
    "backup_file": "configs/claude_code/settings.json.bak"
  },
  "codex": {
    "target_file": "/Users/YOUR_USERNAME/.codex/config.json",
    "backup_file": "configs/codex/config.json.bak"
  }
}
```

**注意**：将 `YOUR_USERNAME` 替换为你的实际用户名。

### 4. 准备配置文件

#### Claude Code 配置

1. 复制模板文件：

```bash
cp configs/claude_code/settings.json.template configs/claude_code/settings_my_config.json
```

2. 编辑配置文件，填入你的 API Key 和其他配置：

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "sk-ant-xxx",
    "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "API_TIMEOUT_MS": "600000"
  }
}
```

#### Codex 配置（可选）

```bash
cp configs/codex/config.json.template configs/codex/config_my_config.json
```

## 使用方法

### 基本用法

```bash
# 交互式选择工具和配置
uv run python switch_ai_config.py

# 或使用 shell 脚本
./AI-coding配置切换器.sh
```

### 命令行参数

```bash
# 指定工具
uv run python switch_ai_config.py -t "claude code"

# 指定工具和配置文件
uv run python switch_ai_config.py -t "claude code" -c settings_580ai.json

# Dry-run 模式（仅预览，不实际执行）
uv run python switch_ai_config.py --dry-run
```

### 参数说明

- `-t, --tool`: 工具名称（claude code / claude / claude_code）
- `-c, --config`: 配置文件名（相对于工具配置目录）
- `--dry-run`: 只展示操作，不写入文件

## 项目结构

```
AIcoding配置切换器/
├── config/                      # 配置切换器本身的配置
│   ├── paths.json.template     # 路径配置模板
│   └── paths.json              # 实际路径配置（不提交到 git）
├── configs/                     # AI 工具配置文件
│   ├── claude_code/
│   │   ├── settings.json.template  # Claude Code 配置模板
│   │   ├── settings_xxx.json       # 你的配置文件
│   │   └── settings.json.bak       # 自动备份
│   └── codex/
│       ├── config.json.template    # Codex 配置模板
│       └── config_xxx.json         # 你的配置文件
├── switch_ai_config.py          # 主程序
├── main.py                      # 入口文件
├── AI-coding配置切换器.sh       # Shell 脚本
├── pyproject.toml               # UV 项目配置
└── README.md                    # 本文件
```

## 工作流程

1. 工具会读取你选择的配置文件
2. 自动备份当前的配置文件到 `configs/*/xxx.bak`
3. 将选择的配置文件复制到目标位置
4. 完成切换

## 注意事项

- ⚠️ 配置文件可能包含敏感信息（API Key），请勿提交到公开仓库
- ✅ 使用 `.gitignore` 已自动排除实际配置文件
- ✅ 只有 `.template` 文件会被提交到 git
- 💡 建议为不同的 API 提供商创建不同的配置文件

## 常见问题

### Q: 如何添加新的配置？

A: 在 `configs/claude_code/` 目录下创建新的 `.json` 文件，然后运行工具选择即可。

### Q: 配置文件在哪里？

A:
- Claude Code: `~/.claude/settings.json`
- 配置切换器: `config/paths.json`

### Q: 如何恢复之前的配置？

A: 备份文件保存在 `configs/*/xxx.bak`，可以通过工具选择 `.bak` 文件恢复。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
