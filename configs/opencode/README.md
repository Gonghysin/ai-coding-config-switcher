# OpenCode 配置文件说明

## 配置文件位置

OpenCode 的配置文件位于：
- **全局配置**: `~/.config/opencode/opencode.json`
- **项目配置**: `./opencode.json`（项目根目录）

## 配置文件格式

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "pincc": {
      "npm": "@ai-sdk/anthropic",
      "name": "PinCC",
      "options": {
        "baseURL": "https://v2-as.pincc.ai/v1",
        "apiKey": "your-api-key-here"
      },
      "models": {
        "claude-sonnet-4-6": {
          "name": "Claude Sonnet 4.6",
          "limit": {
            "context": 200000,
            "output": 8192
          }
        }
      }
    }
  },
  "model": "pincc/claude-sonnet-4-6",
  "small_model": "pincc/claude-sonnet-4-6",
  "autoupdate": true,
  "share": "manual"
}
```

## ⚠️ 重要配置说明

### 使用 @ai-sdk/anthropic 的关键点

1. **baseURL 必须包含 `/v1` 路径**
   - ✅ 正确：`https://v2-as.pincc.ai/v1`
   - ❌ 错误：`https://v2-as.pincc.ai`

2. **必须配置 `small_model`**
   - 避免使用免费的 OpenCode Zen 服务（有速率限制）
   - 建议设置为与主模型相同

3. **建议添加 `limit` 配置**
   - 帮助 OpenCode 正确管理 token 使用
   - `context`: 上下文窗口大小
   - `output`: 最大输出 tokens

## 配置项说明

### provider
配置 AI 提供商信息：
- `npm`: 使用的 AI SDK 包
  - `@ai-sdk/anthropic`: 用于 Anthropic 格式的 API
  - `@ai-sdk/openai-compatible`: 用于 OpenAI 格式的 API
- `name`: 显示名称
- `options.baseURL`: API 端点地址（**使用 @ai-sdk/anthropic 时必须包含 `/v1`**）
- `options.apiKey`: API 密钥
- `models`: 可用模型配置
  - `name`: 模型显示名称
  - `limit.context`: 上下文窗口大小
  - `limit.output`: 最大输出 tokens

### model
指定使用的模型，格式为 `provider/model`，例如：
- `anthropic/claude-sonnet-4-6`
- `anthropic/claude-opus-4-6`
- `openai/gpt-4`

### mcp
配置 MCP (Model Context Protocol) 服务器，用于扩展功能：
- `tavily`: 网络搜索服务
- 可添加更多 MCP 服务

### 其他选项
- `autoupdate`: 是否自动更新 OpenCode
- `share`: 会话分享设置（`manual`/`auto`/`disabled`）

## 使用示例

### 示例 1: 使用 PinCC V2 API（Anthropic 格式）

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "pincc": {
      "npm": "@ai-sdk/anthropic",
      "name": "PinCC V2",
      "options": {
        "baseURL": "https://v2-as.pincc.ai/v1",
        "apiKey": "your-api-key-here"
      },
      "models": {
        "claude-sonnet-4-6": {
          "name": "Claude Sonnet 4.6",
          "limit": {
            "context": 200000,
            "output": 8192
          }
        }
      }
    }
  },
  "model": "pincc/claude-sonnet-4-6",
  "small_model": "pincc/claude-sonnet-4-6"
}
```

**注意**：使用 `@ai-sdk/anthropic` 时，baseURL 必须包含 `/v1` 路径。

### 示例 2: 使用 580AI（OpenAI 格式）

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "ai580": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "580AI",
      "options": {
        "baseURL": "https://cc.580ai.net/v1",
        "apiKey": "your-api-key-here"
      },
      "models": {
        "claude-sonnet-4-6": {
          "name": "Claude Sonnet 4.6"
        }
      }
    }
  },
  "model": "ai580/claude-sonnet-4-6"
}
```

**注意**：使用 `@ai-sdk/openai-compatible` 时，API 必须支持 OpenAI 的 `/v1/chat/completions` 端点。

### 示例 3: 配置多个 MCP 服务

```json
{
  "provider": {
    "anthropic": {
      "apiKey": "{env:ANTHROPIC_API_KEY}",
      "baseURL": "https://api.anthropic.com"
    }
  },
  "model": "anthropic/claude-sonnet-4-6",
  "mcp": {
    "tavily": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.tavily.com/mcp/?tavilyApiKey=xxx"]
    },
    "zai-mcp-server": {
      "command": "npx",
      "args": ["-y", "@zai/mcp-server"]
    }
  }
}
```

## 环境变量

建议将 API Key 设置为环境变量：

```bash
# 添加到 ~/.zshrc 或 ~/.bashrc
export ANTHROPIC_API_KEY="your-api-key-here"
```

然后在配置文件中使用 `{env:ANTHROPIC_API_KEY}` 引用。

## 参考资料

- [OpenCode 官方文档](https://opencode.ai/docs/)
- [OpenCode 配置指南](https://opencode.ai/docs/config/)
- [MCP 服务器列表](https://opencode.ai/docs/mcp-servers/)
