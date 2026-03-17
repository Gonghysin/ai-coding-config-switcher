# AI Coding 配置切换器

一个用于快速切换不同 AI Coding 工具配置的命令行工具，支持 Claude Code、OpenCode 等多种工具。

## 功能特性

- 🔄 快速切换不同的 AI 配置文件
- 💾 自动备份当前配置
- 🎯 支持多种 AI Coding 工具
- 🖥️ 交互式菜单选择
- 🔍 Dry-run 模式预览操作
- 🌐 全局配置合并（权限、MCP 工具等永久配置）

## 支持的工具

- **Claude Code** - Anthropic 官方 CLI 工具
- **OpenCode** - 开源 AI 编码 CLI 工具
- **Codex** - OpenAI Codex（计划支持）

## 项目目录结构

```
ai-coding-config-switcher/
├── .gitignore                   # Git 忽略规则
├── .python-version              # Python 版本配置
├── README.md                    # 项目说明文档
├── pyproject.toml               # UV 项目配置和依赖
├── uv.lock                      # UV 依赖锁定文件
├── main.py                      # 程序入口文件
├── switch_ai_config.py          # 核心切换逻辑
├── AI-coding配置切换器.sh       # Shell 快捷脚本
└── configs/                     # 配置文件目录
    ├── config/                  # 配置切换器本身的配置
    │   ├── paths.json.template  # 路径配置模板（需复制并填写）
    │   └── paths.json           # 实际路径配置（不提交到 git）
    ├── claude_code/             # Claude Code 配置文件
    │   ├── settings.json.template      # 配置模板
    │   ├── global_settings.json        # 全局配置（权限等永久配置）
    │   ├── settings_xxx.json           # 你的配置文件（可多个）
    │   └── settings.json.bak           # 自动备份文件
    ├── opencode/                # OpenCode 配置文件
    │   ├── opencode.json.template      # 配置模板
    │   ├── global_settings.json        # 全局配置（权限等永久配置）
    │   ├── opencode_xxx.json           # 你的配置文件（可多个）
    │   ├── opencode.json.bak           # 自动备份文件
    │   └── README.md                   # OpenCode 配置说明
    └── codex/                   # Codex 配置文件（计划支持）
        ├── config.json.template        # 配置模板
        └── config_xxx.json             # 你的配置文件（可多个）
```

### 文件说明

| 文件/目录 | 说明 |
|----------|------|
| `switch_ai_config.py` | 主程序，包含配置切换的核心逻辑 |
| `main.py` | 程序入口，可直接运行 |
| `AI-coding配置切换器.sh` | Shell 脚本，提供快捷启动方式 |
| `configs/config/paths.json` | 配置切换器的路径配置，指定各工具的配置文件位置 |
| `configs/claude_code/` | 存放 Claude Code 的多个配置文件 |
| `configs/opencode/` | 存放 OpenCode 的多个配置文件 |
| `configs/codex/` | 存放 Codex 的多个配置文件 |
| `.template` 文件 | 配置模板，需复制并填写实际值 |
| `.bak` 文件 | 自动生成的备份文件 |

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
cp configs/config/paths.json.template configs/config/paths.json
```

2. 编辑 `configs/config/paths.json`，填入你的实际路径：

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

#### OpenCode 配置

1. 复制模板文件：

```bash
cp configs/opencode/opencode.json.template configs/opencode/opencode_my_config.json
```

2. 编辑配置文件，填入你的配置：

```json
{
  "provider": {
    "anthropic": {
      "apiKey": "{env:ANTHROPIC_API_KEY}",
      "baseURL": "https://api.anthropic.com",
      "timeout": 600000
    }
  },
  "model": "anthropic/claude-sonnet-4-6",
  "mcp": {
    "tavily": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp.tavily.com/mcp/?tavilyApiKey=YOUR_TAVILY_API_KEY"
      ]
    }
  },
  "autoupdate": true,
  "share": "manual"
}
```

**注意**：
- OpenCode 配置文件位于 `~/.config/opencode/opencode.json`
- 建议使用环境变量 `{env:ANTHROPIC_API_KEY}` 引用 API Key
- 详细配置说明请查看 `configs/opencode/README.md`

### 5. 设置 Shell 脚本（可选）

为了方便使用，项目提供了一个 Shell 脚本快捷方式。

#### 添加执行权限

```bash
chmod +x AI-coding配置切换器.sh
```

#### 创建全局命令（可选）

你可以创建一个软链接，让脚本在任何地方都能使用：

```bash
# 方式1: 添加到 /usr/local/bin（推荐）
sudo ln -s "$(pwd)/AI-coding配置切换器.sh" /usr/local/bin/ai-config

# 方式2: 添加到用户 bin 目录
mkdir -p ~/bin
ln -s "$(pwd)/AI-coding配置切换器.sh" ~/bin/ai-config
# 确保 ~/bin 在你的 PATH 中

# 之后就可以在任何地方使用
ai-config
```

**脚本说明：**
- 脚本会自动检测 uv 是否安装
- 自动切换到项目目录
- 支持传递所有命令行参数
- 无需手动指定项目路径（自动识别）

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
uv run python switch_ai_config.py -t "opencode"

# 指定工具和配置文件
uv run python switch_ai_config.py -t "claude code" -c settings_580ai.json
uv run python switch_ai_config.py -t "opencode" -c opencode_custom.json

# Dry-run 模式（仅预览，不实际执行）
uv run python switch_ai_config.py --dry-run
```

### 参数说明

- `-t, --tool`: 工具名称（claude code / opencode / codex）
- `-c, --config`: 配置文件名（相对于工具配置目录）
- `--dry-run`: 只展示操作，不写入文件

## 工作流程

1. 工具会读取你选择的配置文件
2. 加载全局配置文件（`global_settings.json`）
3. 将选择的配置与全局配置合并（全局配置优先级更高）
4. 自动备份当前的配置文件到 `configs/*/xxx.bak`
5. 将合并后的配置文件复制到目标位置
6. 完成切换

## 全局配置功能

### 什么是全局配置？

全局配置文件（`global_settings.json`）用于存放所有配置都需要的永久性设置，例如：
- 权限配置（`permissions.allow`）
- MCP 工具白名单
- 其他通用设置

### 为什么需要全局配置？

当你频繁切换不同的 API 配置时，某些设置（如联网搜索权限）需要在所有配置中保持一致。全局配置可以避免在每个配置文件中重复添加这些设置。

### 如何使用全局配置？

1. 编辑 `configs/claude_code/global_settings.json`：

```json
{
  "permissions": {
    "allow": [
      "WebSearch",
      "WebFetch",
      "mcp__tavily__tavily_search",
      "mcp__tavily__tavily_extract",
      "mcp__tavily__tavily_crawl",
      "mcp__tavily__tavily_map",
      "mcp__tavily__tavily_research"
    ]
  }
}
```

2. 创建你的单个配置文件（只包含 API 相关配置）：

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
    "ANTHROPIC_BASE_URL": "https://api.example.com"
  },
  "model": "claude-sonnet-4-6"
}
```

3. 切换配置时，工具会自动合并两者：

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "sk-xxx",
    "ANTHROPIC_BASE_URL": "https://api.example.com"
  },
  "model": "claude-sonnet-4-6",
  "permissions": {
    "allow": [
      "WebSearch",
      "WebFetch",
      "mcp__tavily__tavily_search",
      ...
    ]
  }
}
```

### 配置合并规则

- **字典类型**：递归合并，全局配置覆盖单个配置
- **列表类型**：合并并去重，保持顺序
- **其他类型**：全局配置直接覆盖

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
- 配置切换器: `configs/config/paths.json`

### Q: 如何恢复之前的配置？

A: 备份文件保存在 `configs/*/xxx.bak`，可以通过工具选择 `.bak` 文件恢复。

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
