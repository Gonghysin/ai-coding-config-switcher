#!/usr/bin/env python3
"""
AI Coding 配置切换器 - 配置切换模块
支持两级目录结构：提供商 -> 模型
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import toml

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.columns import Columns
from rich import box as rich_box

console = Console()

PROJECT_ROOT = Path(__file__).resolve().parent
CLAUDE_CODE_CONFIG_DIR = PROJECT_ROOT / "configs" / "claude_code"
OPENCODE_CONFIG_DIR = PROJECT_ROOT / "configs" / "opencode"
CODEX_CONFIG_DIR = PROJECT_ROOT / "configs" / "codex"

# 配置文件路径
OPENCODE_TARGET_FILE = Path.home() / ".config" / "opencode" / "opencode.json"
CODEX_TARGET_FILE = Path.home() / ".codex" / "config.toml"
CODEX_AUTH_FILE = Path.home() / ".codex" / "auth.json"


def get_caller_dir() -> Path:
    """获取用户调用脚本时所在的目录（通过 shell 脚本传入 CALLER_DIR 环境变量）"""
    caller = os.environ.get("CALLER_DIR")
    if caller:
        return Path(caller)
    return Path.cwd()


def get_config_dir(tool: str) -> Path:
    """根据工具名称获取配置目录"""
    if tool == "opencode":
        return OPENCODE_CONFIG_DIR
    elif tool == "codex":
        return CODEX_CONFIG_DIR
    return CLAUDE_CODE_CONFIG_DIR


def normalize_provider_config(config: dict, tool: str = "claude code") -> dict:
    """标准化提供商配置，将旧格式 api_key 转换为新格式 api_keys 数组"""
    if "api_key" in config and "api_keys" not in config:
        api_key = config.pop("api_key")
        config["api_keys"] = [{"key": api_key, "alias": "默认"}] if api_key else []
    elif "api_keys" not in config:
        config["api_keys"] = []
    if tool == "codex":
        config.setdefault("auth_mode", "openai")
    return config


def get_provider_config(provider: str, tool: str = "claude code") -> dict:
    """获取提供商配置（自动将旧格式 api_key 迁移为 api_keys）"""
    config_dir = get_config_dir(tool)
    config_file = config_dir / provider / "config.json"
    if not config_file.exists():
        if tool == "codex":
            return {"auth_mode": "openai", "api_url": "", "api_keys": [], "models": []}
        return {"api_url": "", "api_keys": [], "models": []}
    config = json.loads(config_file.read_text(encoding="utf-8"))
    return normalize_provider_config(config, tool)


def get_global_settings(tool: str = "claude code") -> dict:
    """读取全局配置文件 global_settings.json"""
    config_dir = get_config_dir(tool)
    global_settings_file = config_dir / "global_settings.json"
    if global_settings_file.exists():
        return json.loads(global_settings_file.read_text(encoding="utf-8"))
    return {}


def deep_merge(base: dict, override: dict) -> dict:
    """深度合并两个字典，override 的值会覆盖 base 的值"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def list_providers(tool: str = "claude code") -> list[str]:
    """列出所有提供商"""
    config_dir = get_config_dir(tool)
    if not config_dir.exists():
        return []
    providers = [
        p.name for p in config_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ]
    return sorted(providers)


def list_models(provider: str, tool: str = "claude code") -> list[dict]:
    """列出提供商下的所有模型"""
    config = get_provider_config(provider, tool)
    return config.get("models", [])


def list_api_keys(provider: str, tool: str = "claude code") -> list[dict]:
    """列出提供商下的所有 API Key"""
    config = get_provider_config(provider, tool)
    return config.get("api_keys", [])


def generate_settings(provider: str, model_name: str, api_key: str = "") -> dict:
    """生成Claude Code的settings.json配置（包含 env、permissions、hooks 等）"""
    config = get_provider_config(provider, "claude code")

    model_exists = any(m["name"] == model_name for m in config.get("models", []))
    if not model_exists:
        raise ValueError(f"模型 '{model_name}' 不存在于提供商 '{provider}'")

    global_settings = get_global_settings("claude code")

    # 优先使用传入的 api_key，否则取第一个可用 Key
    effective_key = api_key
    if not effective_key:
        api_keys = config.get("api_keys", [])
        if api_keys:
            effective_key = api_keys[0].get("key", "")

    env_settings: dict = {"env": {}}
    if effective_key:
        env_settings["env"]["ANTHROPIC_AUTH_TOKEN"] = effective_key
    if config.get("api_url"):
        env_settings["env"]["ANTHROPIC_BASE_URL"] = config["api_url"]

    env_settings["env"]["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    env_settings["env"]["API_TIMEOUT_MS"] = "600000"
    env_settings["env"]["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model_name

    settings = deep_merge(env_settings, global_settings)
    return settings


def generate_opencode_settings(provider: str, model_name: str, api_key: str = "") -> dict:
    """生成 opencode 的配置文件

    opencode 配置格式：
    {
        "model": "provider-type/model-name",
        "enabled_providers": ["provider-type"],
        "provider": {
            "provider-type": {
                "options": {
                    "baseURL": "...",
                    "apiKey": "..."
                }
            }
        }
    }
    """
    config = get_provider_config(provider, "opencode")

    model_exists = any(m["name"] == model_name for m in config.get("models", []))
    if not model_exists:
        raise ValueError(f"模型 '{model_name}' 不存在于提供商 '{provider}'")

    global_settings = get_global_settings("opencode")

    # 优先使用传入的 api_key，否则取第一个可用 Key
    effective_key = api_key
    if not effective_key:
        api_keys = config.get("api_keys", [])
        if api_keys:
            effective_key = api_keys[0].get("key", "")

    # opencode 的 provider key 必须是标准类型
    # 使用 "openai" 作为通用 OpenAI 兼容 API 的 provider type
    provider_key = "openai"

    # 构建 opencode 配置
    opencode_config: dict = {
        "model": f"{provider_key}/{model_name}",
        "enabled_providers": [provider_key],
        "provider": {
            provider_key: {
                "options": {
                    "baseURL": config.get("api_url", ""),
                    "apiKey": effective_key,
                }
            }
        }
    }

    # 合并全局设置
    if global_settings:
        opencode_config = deep_merge(opencode_config, global_settings)

    return opencode_config


def generate_codex_settings(provider: str, model_name: str, api_key: str = "") -> dict:
    """生成 Codex 的 config.toml 配置

    Codex provider 认证模式：
    - openai: 使用 ~/.codex/auth.json 中的 OpenAI 登录态 / API Key
    - bearer_token: 将第三方 provider token 写入 model provider
    """
    config = get_provider_config(provider, "codex")

    model_exists = any(m["name"] == model_name for m in config.get("models", []))
    if not model_exists:
        raise ValueError(f"模型 '{model_name}' 不存在于提供商 '{provider}'")

    global_settings = get_global_settings("codex")

    # 优先使用传入的 api_key，否则取第一个可用 Key
    effective_key = api_key
    if not effective_key:
        api_keys = config.get("api_keys", [])
        if api_keys:
            effective_key = api_keys[0].get("key", "")

    auth_mode = config.get("auth_mode", "openai")

    # Codex 使用固定的 provider key "crs"
    provider_key = "crs"

    provider_config: dict = {
        "name": provider_key,
        "base_url": config.get("api_url", ""),
        "wire_api": "responses",
    }

    if auth_mode == "openai":
        provider_config["requires_openai_auth"] = True
    elif auth_mode == "bearer_token":
        if not effective_key:
            raise ValueError(f"Codex 提供商 '{provider}' 使用 bearer_token 模式时必须提供 API Key")
        provider_config["experimental_bearer_token"] = effective_key
    else:
        raise ValueError(
            f"Codex 提供商 '{provider}' 的 auth_mode 无效: {auth_mode}，支持: openai / bearer_token"
        )

    # 构建 Codex 配置
    codex_config: dict = {
        "model_provider": provider_key,
        "model": model_name,
        "model_providers": {
            provider_key: provider_config
        }
    }

    # 合并全局设置
    if global_settings:
        codex_config = {**global_settings, **codex_config}

    return codex_config


def build_codex_auth_settings(api_key: str) -> dict:
    """生成 Codex 的 auth.json 内容，保留已有字段并更新 OPENAI_API_KEY。"""
    auth_settings: dict = {}
    if CODEX_AUTH_FILE.exists():
        auth_settings = json.loads(CODEX_AUTH_FILE.read_text(encoding="utf-8"))
    auth_settings["OPENAI_API_KEY"] = api_key
    return auth_settings


# ──────────────────────────────────────────────
# TUI 组件
# ──────────────────────────────────────────────

def print_header() -> None:
    """打印应用标题栏"""
    console.print()
    console.print(Panel(
        "[bold cyan]AI Coding 配置切换器[/bold cyan]\n"
        "[dim]快速切换 AI 编程工具的 API 配置[/dim]",
        border_style="cyan",
        expand=False,
        padding=(0, 2),
    ))


def pick_from_menu(
    options: list[str],
    title: str,
    allow_open_folder: bool = False,
    folder_path: Path | None = None,
    extra_options: list[str] | None = None,
    allow_back: bool = False,
) -> tuple[str, int]:
    """从菜单中选择，返回 (选项名, 选项索引)。返回 ('__BACK__', -1) 表示返回上一页"""
    all_options = list(options)
    extra_start_idx = len(all_options)
    if extra_options:
        all_options.extend(extra_options)

    if not all_options and not allow_back:
        raise ValueError("没有可选项")

    while True:
        table = Table(
            show_header=False,
            box=rich_box.ROUNDED,
            padding=(0, 1),
            border_style="bright_black",
            expand=False,
        )
        table.add_column("编号", style="bold cyan", width=4, no_wrap=True)
        table.add_column("选项")

        # 特殊操作：打开文件夹（0）或返回上一页（b）
        special_rows: list[str] = []
        if allow_open_folder and folder_path:
            special_rows.append("open_folder")
            table.add_row("[dim]0[/dim]", "[dim]📂  打开配置文件夹（访达）[/dim]")
        if allow_back:
            table.add_row("[dim]b[/dim]", "[dim]← 返回上一页[/dim]")

        for idx, item in enumerate(options, start=1):
            table.add_row(str(idx), item)

        if extra_options:
            table.add_section()
            for i, item in enumerate(extra_options):
                idx = extra_start_idx + 1 + i
                table.add_row(
                    f"[dim]{idx}[/dim]",
                    f"[dim]{item}[/dim]",
                )

        console.print()
        console.print(Panel(table, title=f"[bold]{title}[/bold]", border_style="blue", expand=False))

        raw = Prompt.ask("[cyan]请输入编号[/cyan]").strip().lower()
        if raw == "b" and allow_back:
            return "__BACK__", -1
        if not raw.isdigit():
            console.print("[red]输入无效，请输入数字编号。[/red]")
            continue
        choice = int(raw)

        if choice == 0 and allow_open_folder and folder_path:
            open_folder_in_finder(folder_path)
            console.print(f"[green]已在访达中打开:[/green] {folder_path}")
            continue

        if 1 <= choice <= len(all_options):
            return all_options[choice - 1], choice
        console.print("[red]编号超出范围，请重新输入。[/red]")


def normalize_tool_name(user_input: str) -> str | None:
    """标准化工具名称"""
    text = user_input.strip().lower()
    mapping = {
        "claude": "claude code",
        "claude code": "claude code",
        "claude_code": "claude code",
        "opencode": "opencode",
        "open code": "opencode",
        "open_code": "opencode",
        "codex": "codex",
    }
    return mapping.get(text)


def open_folder_in_finder(folder_path: Path) -> None:
    """在访达中打开文件夹"""
    try:
        subprocess.run(["open", str(folder_path)], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]警告: 无法打开文件夹: {e}[/yellow]")


def list_tools() -> list[str]:
    """列出所有支持的工具"""
    return ["claude code", "opencode", "codex"]


# ──────────────────────────────────────────────
# 交互式管理操作
# ──────────────────────────────────────────────

def interactive_add_provider(tool: str) -> str:
    """交互式添加提供商"""
    console.print(Panel("[bold]添加新提供商[/bold]", border_style="green", expand=False))

    name = Prompt.ask("  提供商名称").strip()
    if not name:
        console.print("[red]提供商名称不能为空[/red]")
        return ""

    config_dir = get_config_dir(tool)
    if (config_dir / name).exists():
        console.print(f"[yellow]提供商 '{name}' 已存在[/yellow]")
        return name

    api_url = Prompt.ask("  API URL [dim](留空跳过)[/dim]", default="").strip()
    auth_mode = "openai"
    if tool == "codex":
        auth_mode = Prompt.ask(
            "  Codex 认证模式 [dim](openai / bearer_token)[/dim]",
            choices=["openai", "bearer_token"],
            default="openai",
        ).strip()

    # 询问是否添加第一个 API Key
    api_keys = []
    if Confirm.ask("  是否现在添加 API Key？", default=True):
        alias = Prompt.ask("  API Key 别名 [dim](如: 免费版、Pro版)[/dim]", default="默认").strip()
        api_key = Prompt.ask("  API Key", password=True, default="").strip()
        if api_key:
            api_keys.append({"key": api_key, "alias": alias or "默认"})

    # 创建目录并写入配置
    provider_dir = config_dir / name
    provider_dir.mkdir(parents=True, exist_ok=True)
    config = {"api_url": api_url, "api_keys": api_keys, "models": []}
    if tool == "codex":
        config["auth_mode"] = auth_mode
    (provider_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    console.print(f"[green]✓ 已添加提供商:[/green] {name}")
    return name


def interactive_edit_provider(provider: str, tool: str) -> None:
    """交互式编辑提供商（编辑 API URL；API Key 通过独立菜单管理）"""
    console.print(Panel(f"[bold]编辑提供商:[/bold] {provider}", border_style="yellow", expand=False))

    config = get_provider_config(provider, tool)
    current_url = config.get("api_url", "")
    updated = config.copy()

    new_url = Prompt.ask("  API URL", default=current_url).strip()
    updated["api_url"] = new_url

    if tool == "codex":
        updated["auth_mode"] = Prompt.ask(
            "  Codex 认证模式",
            choices=["openai", "bearer_token"],
            default=config.get("auth_mode", "openai"),
        ).strip()

    if updated != config:
        _save_provider_config(provider, tool, updated)
        console.print("[green]✓ 已更新提供商配置[/green]")
    else:
        console.print("[dim]未做任何修改[/dim]")


def interactive_add_model(provider: str, tool: str) -> str:
    """交互式添加模型，返回模型名称"""
    console.print(Panel(f"[bold]添加模型到:[/bold] {provider}", border_style="green", expand=False))

    model_name = Prompt.ask("  模型名称").strip()
    if not model_name:
        console.print("[red]模型名称不能为空[/red]")
        return ""

    alias = Prompt.ask("  别名 [dim](留空使用模型名)[/dim]", default="").strip()

    config = get_provider_config(provider, tool)
    existing = [m["name"] for m in config.get("models", [])]
    if model_name in existing:
        console.print(f"[yellow]模型 '{model_name}' 已存在[/yellow]")
        return model_name

    new_model = {"name": model_name, "alias": alias or model_name}
    updated = {**config, "models": [*config.get("models", []), new_model]}
    _save_provider_config(provider, tool, updated)
    console.print(f"[green]✓ 已添加模型:[/green] {model_name}")
    return model_name


def interactive_delete_provider(provider: str, tool: str) -> bool:
    """交互式删除提供商"""
    if Confirm.ask(f"  [yellow]确定要删除提供商 '{provider}' 吗？[/yellow]", default=False):
        provider_dir = get_config_dir(tool) / provider
        if provider_dir.exists():
            shutil.rmtree(provider_dir)
        console.print(f"[green]✓ 已删除提供商:[/green] {provider}")
        return True
    return False


def interactive_delete_model(provider: str, model_name: str, tool: str) -> bool:
    """交互式删除模型"""
    if Confirm.ask(f"  [yellow]确定要删除模型 '{model_name}' 吗？[/yellow]", default=False):
        config = get_provider_config(provider, tool)
        updated_models = [m for m in config.get("models", []) if m["name"] != model_name]
        _save_provider_config(provider, tool, {**config, "models": updated_models})
        console.print(f"[green]✓ 已删除模型:[/green] {model_name}")
        return True
    return False


def _save_provider_config(provider: str, tool: str, config: dict) -> None:
    """将提供商配置写回磁盘"""
    config_dir = get_config_dir(tool)
    config_file = config_dir / provider / "config.json"
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def interactive_add_api_key(provider: str, tool: str) -> str:
    """交互式添加 API Key，返回新 key 值"""
    console.print(Panel(f"[bold]添加 API Key 到:[/bold] {provider}", border_style="green", expand=False))
    alias = Prompt.ask("  别名 [dim](如: 免费版、Pro版)[/dim]").strip()
    if not alias:
        console.print("[red]别名不能为空[/red]")
        return ""
    key = Prompt.ask("  API Key", password=True).strip()
    if not key:
        console.print("[red]API Key 不能为空[/red]")
        return ""
    config = get_provider_config(provider, tool)
    existing_aliases = [k.get("alias", "") for k in config.get("api_keys", [])]
    if alias in existing_aliases:
        console.print(f"[yellow]别名 '{alias}' 已存在，将覆盖原有 Key[/yellow]")
        new_keys = [
            {"key": key, "alias": alias} if k.get("alias") == alias else k
            for k in config["api_keys"]
        ]
        config = {**config, "api_keys": new_keys}
    else:
        config = {**config, "api_keys": [*config.get("api_keys", []), {"key": key, "alias": alias}]}
    _save_provider_config(provider, tool, config)
    console.print(f"[green]✓ 已添加 API Key:[/green] {alias}")
    return key


def interactive_edit_api_key(provider: str, tool: str) -> None:
    """交互式编辑 API Key"""
    keys = list_api_keys(provider, tool)
    if not keys:
        console.print("[yellow]该提供商暂无 API Key[/yellow]")
        return
    aliases = [k.get("alias", k.get("key", "")[:8] + "...") for k in keys]
    selected, idx = pick_from_menu(aliases, f"选择要编辑的 API Key  [dim](提供商: {provider})[/dim]", allow_back=True)
    if selected == "__BACK__":
        return
    chosen = keys[idx - 1]
    new_alias = Prompt.ask("  新别名 [dim](留空保持不变)[/dim]", default="").strip()
    new_key = Prompt.ask("  新 API Key [dim](留空保持不变)[/dim]", default="", password=True).strip()
    config = get_provider_config(provider, tool)
    updated_keys = []
    for k in config["api_keys"]:
        if k.get("alias") == chosen.get("alias") and k.get("key") == chosen.get("key"):
            updated = {
                "key": new_key if new_key else k["key"],
                "alias": new_alias if new_alias else k.get("alias", ""),
            }
            updated_keys.append(updated)
        else:
            updated_keys.append(k)
    config = {**config, "api_keys": updated_keys}
    _save_provider_config(provider, tool, config)
    console.print("[green]✓ 已更新 API Key[/green]")


def interactive_delete_api_key(provider: str, tool: str) -> None:
    """交互式删除 API Key"""
    keys = list_api_keys(provider, tool)
    if not keys:
        console.print("[yellow]该提供商暂无 API Key[/yellow]")
        return
    aliases = [k.get("alias", k.get("key", "")[:8] + "...") for k in keys]
    selected, idx = pick_from_menu(aliases, f"选择要删除的 API Key  [dim](提供商: {provider})[/dim]", allow_back=True)
    if selected == "__BACK__":
        return
    chosen = keys[idx - 1]
    alias = chosen.get("alias", selected)
    if Confirm.ask(f"  [yellow]确定要删除 API Key '{alias}' 吗？[/yellow]", default=False):
        config = get_provider_config(provider, tool)
        new_keys = [k for k in config["api_keys"] if not (k.get("alias") == chosen.get("alias") and k.get("key") == chosen.get("key"))]
        config = {**config, "api_keys": new_keys}
        _save_provider_config(provider, tool, config)
        console.print(f"[green]✓ 已删除 API Key:[/green] {alias}")


def resolve_api_key(provider: str, tool: str) -> str | None:
    """交互式选择 API Key，返回 key 字符串。返回 '__BACK__' 表示返回上一页，None 表示重试，'' 表示不使用 API Key"""
    keys = list_api_keys(provider, tool)

    NO_KEY_OPTION = "不使用 API Key（官方订阅账号登录）"

    extra_options = [
        "+ 添加新 API Key",
        "+ 编辑 API Key",
        "+ 删除 API Key",
    ]

    if not keys:
        result, _ = pick_from_menu(
            [NO_KEY_OPTION],
            f"选择 API Key  [dim](提供商: {provider})[/dim]",
            extra_options=["+ 添加新 API Key"],
            allow_back=True,
        )
        if result == "__BACK__":
            return "__BACK__"
        if result == NO_KEY_OPTION:
            return ""
        if result == "+ 添加新 API Key":
            interactive_add_api_key(provider, tool)
        return None

    key_displays = [
        f"{k.get('alias', '未命名')}  [dim]({k.get('key', '')[:8]}...)[/dim]"
        for k in keys
    ]
    display_options = [NO_KEY_OPTION] + key_displays

    result, choice = pick_from_menu(
        display_options,
        f"选择 API Key  [dim](提供商: {provider})[/dim]",
        extra_options=extra_options,
        allow_back=True,
    )

    if result == "__BACK__":
        return "__BACK__"
    if result == NO_KEY_OPTION:
        return ""
    if result == "+ 添加新 API Key":
        interactive_add_api_key(provider, tool)
        return None
    if result == "+ 编辑 API Key":
        interactive_edit_api_key(provider, tool)
        return None
    if result == "+ 删除 API Key":
        interactive_delete_api_key(provider, tool)
        return None

    # 选中某个 Key（choice 从 1 起，NO_KEY_OPTION 占位 choice=1，key 从 choice=2 开始）
    key_idx = choice - 2
    selected_key = keys[key_idx].get("key", "")
    return selected_key if selected_key else None


# ──────────────────────────────────────────────
# 交互式选择流程
# ──────────��───────────────────────────────────

def resolve_tool() -> str:
    """交互式选择工具"""
    tools = list_tools()
    result, _ = pick_from_menu(tools, "选择目标 AI Coding 工具")
    return result


def resolve_scope(tool: str) -> tuple[str, Path] | None:
    """交互式选择写入范围，返回 (scope_name, target_file)，返回 None 表示返回上一页"""
    caller_dir = get_caller_dir()

    if tool == "opencode":
        scope_options = [
            f"系统级  [dim](~/.config/opencode/opencode.json — 对所有项目生效)[/dim]",
            f"项目级  [dim]({caller_dir / 'opencode.json'} — 仅当前项目，可提交 Git)[/dim]",
        ]
        result, choice = pick_from_menu(scope_options, "选择配置写入范围", allow_back=True)
        if result == "__BACK__":
            return None
        if choice == 1:
            return "system", Path.home() / ".config" / "opencode" / "opencode.json"
        else:
            return "project", caller_dir / "opencode.json"
    elif tool == "codex":
        scope_options = [
            f"系统级  [dim](~/.codex/config.toml — 对所有项目生效)[/dim]",
            f"项目级  [dim]({caller_dir / '.codex/config.toml'} — 仅当前项目，优先于系统级)[/dim]",
        ]
        result, choice = pick_from_menu(scope_options, "选择配置写入范围", allow_back=True)
        if result == "__BACK__":
            return None
        if choice == 1:
            return "system", Path.home() / ".codex" / "config.toml"
        return "project", caller_dir / ".codex" / "config.toml"
    else:
        scope_options = [
            f"系统级  [dim](~/.claude/settings.json — 对所有项目生效)[/dim]",
            f"项目级  [dim]({caller_dir / '.claude/settings.json'} — 仅当前项目，可提交 Git)[/dim]",
            f"项目本地 [dim]({caller_dir / '.claude/settings.local.json'} — 仅当前项目，不提交 Git)[/dim]",
        ]
        result, choice = pick_from_menu(scope_options, "选择配置写入范围", allow_back=True)
        if result == "__BACK__":
            return None
        if choice == 1:
            return "system", Path.home() / ".claude" / "settings.json"
        elif choice == 2:
            return "project", caller_dir / ".claude" / "settings.json"
        else:
            return "project-local", caller_dir / ".claude" / "settings.local.json"


def resolve_provider(tool: str) -> str | None:
    """交互式选择提供商，返回 None 表示需要重试，返回 '__BACK__' 表示返回上一页"""
    providers = list_providers(tool)
    config_dir = get_config_dir(tool)

    extra_options = [
        "+ 添加新提供商",
        "+ 编辑提供商配置",
        "+ 删除提供商",
    ]

    if not providers:
        result, _ = pick_from_menu(
            [], f"选择 AI 服务提供商  [dim](工具: {tool})[/dim]",
            extra_options=["+ 添加新提供商"],
            allow_back=True,
        )
        if result == "__BACK__":
            return "__BACK__"
        if result == "+ 添加新提供商":
            name = interactive_add_provider(tool)
            return name or None
        return None

    result, choice = pick_from_menu(
        providers,
        f"选择 AI 服务提供商  [dim](工具: {tool})[/dim]",
        allow_open_folder=True,
        folder_path=config_dir,
        extra_options=extra_options,
        allow_back=True,
    )

    if result == "__BACK__":
        return "__BACK__"
    if result == "+ 添加新提供商":
        name = interactive_add_provider(tool)
        return name or None
    elif result == "+ 编辑提供商配置":
        if providers:
            selected, _ = pick_from_menu(providers, "选择要编辑的提供商", allow_back=True)
            if selected != "__BACK__":
                interactive_edit_provider(selected, tool)
        return None
    elif result == "+ 删除提供商":
        if providers:
            selected, _ = pick_from_menu(providers, "选择要删除的提供商", allow_back=True)
            if selected != "__BACK__":
                interactive_delete_provider(selected, tool)
        return None

    return result


def resolve_model(provider: str, tool: str) -> str | None:
    """交互式选择模型，返回 None 表示需要重试，返回 '__BACK__' 表示返回上一页"""
    models = list_models(provider, tool)

    extra_options = [
        "+ 添加新模型",
        "+ 编辑模型别名",
        "+ 删除模型",
    ]

    if not models:
        result, _ = pick_from_menu(
            [], f"选择模型  [dim](提供商: {provider})[/dim]",
            extra_options=["+ 添加新模型"],
            allow_back=True,
        )
        if result == "__BACK__":
            return "__BACK__"
        if result == "+ 添加新模型":
            interactive_add_model(provider, tool)
        return None

    model_options = [
        f"{m['name']}  [dim]({m.get('alias', m['name'])})[/dim]"
        if m.get("alias") and m.get("alias") != m["name"]
        else m["name"]
        for m in models
    ]

    result, choice = pick_from_menu(
        model_options,
        f"选择模型  [dim](提供商: {provider})[/dim]",
        extra_options=extra_options,
        allow_back=True,
    )

    if result == "__BACK__":
        return "__BACK__"
    if result == "+ 添加新模型":
        interactive_add_model(provider, tool)
        return None
    elif result == "+ 编辑模型别名":
        if models:
            sel, _ = pick_from_menu(model_options, "选择要编辑的模型", allow_back=True)
            if sel != "__BACK__":
                model_name = models[model_options.index(sel)]["name"]
                model_info = next((m for m in models if m["name"] == model_name), None)
                if model_info:
                    new_alias = Prompt.ask(
                        "  新别名", default=model_info.get("alias", model_name)
                    ).strip()
                    if new_alias:
                        config = get_provider_config(provider, tool)
                        updated_models = [
                            {**m, "alias": new_alias} if m["name"] == model_name else m
                            for m in config.get("models", [])
                        ]
                        _save_provider_config(provider, tool, {**config, "models": updated_models})
                        console.print(f"[green]✓ 已更新别名:[/green] {new_alias}")
        return None
    elif result == "+ 删除模型":
        if models:
            sel, _ = pick_from_menu(model_options, "选择要删除的模型", allow_back=True)
            if sel != "__BACK__":
                model_name = models[model_options.index(sel)]["name"]
                interactive_delete_model(provider, model_name, tool)
        return None

    # 提取真实模型名（去掉 rich markup）
    idx = model_options.index(result)
    return models[idx]["name"]


# ──────────────────────────────────────────────
# 核心切换逻辑
# ──────────────────────────────────────────────

def switch_config(provider: str, model_name: str, dry_run: bool, scope: str, target_file: Path, tool: str, api_key: str = "") -> None:
    """切换配置"""
    config_dir = get_config_dir(tool)
    backup_file = config_dir / provider / f"settings.{scope}.bak"
    auth_file: Path | None = None
    auth_content = ""
    auth_backup_file = config_dir / provider / f"auth.{scope}.bak"

    # 根据 tool 生成不同的配置格式
    if tool == "opencode":
        settings = generate_opencode_settings(provider, model_name, api_key)
        settings_content = json.dumps(settings, indent=2, ensure_ascii=False)
        is_toml = False
    elif tool == "codex":
        provider_config = get_provider_config(provider, "codex")
        effective_key = api_key
        if not effective_key:
            api_keys = provider_config.get("api_keys", [])
            if api_keys:
                effective_key = api_keys[0].get("key", "")
        settings = generate_codex_settings(provider, model_name, api_key)
        settings_content = toml.dumps(settings)
        is_toml = True
        if provider_config.get("auth_mode", "openai") == "openai" and effective_key:
            auth_file = CODEX_AUTH_FILE
            auth_content = json.dumps(
                build_codex_auth_settings(effective_key),
                indent=2,
                ensure_ascii=False,
            )
    else:
        settings = generate_settings(provider, model_name, api_key)
        settings_content = json.dumps(settings, indent=2, ensure_ascii=False)
        is_toml = False

    settings_data = settings_content.encode("utf-8")

    if dry_run:
        console.print()
        console.print(Panel(
            f"[bold cyan]Dry Run 预览[/bold cyan]\n\n"
            f"  提供商: [yellow]{provider}[/yellow]\n"
            f"  模型:   [yellow]{model_name}[/yellow]\n"
            f"  工具:   [yellow]{tool}[/yellow]\n"
            f"  范围:   [yellow]{scope}[/yellow]\n"
            f"  目标:   [dim]{target_file}[/dim]"
            + (f"\n  备份:   [dim]{backup_file}[/dim]" if target_file.exists() else "")
            + (f"\n  认证:   [dim]{auth_file}[/dim]" if auth_file else ""),
            border_style="cyan",
            expand=False,
        ))
        console.print()
        console.print(Panel(
            Text(settings_content),
            title="[bold]配置内容预览[/bold]",
            border_style="bright_black",
        ))
        if auth_file:
            console.print()
            console.print(Panel(
                Text(auth_content),
                title="[bold]auth.json 预览[/bold]",
                border_style="bright_black",
            ))
        return

    target_file.parent.mkdir(parents=True, exist_ok=True)
    backup_file.parent.mkdir(parents=True, exist_ok=True)

    if target_file.exists():
        shutil.copy2(target_file, backup_file)
        console.print(f"[dim]已备份当前配置: {backup_file}[/dim]")

    if auth_file:
        auth_file.parent.mkdir(parents=True, exist_ok=True)
        auth_backup_file.parent.mkdir(parents=True, exist_ok=True)
        if auth_file.exists():
            shutil.copy2(auth_file, auth_backup_file)
            console.print(f"[dim]已备份当前认证: {auth_backup_file}[/dim]")

    if scope == "project-local":
        _ensure_gitignore(target_file.parent)

    target_file.write_bytes(settings_data)
    if auth_file:
        auth_file.write_text(auth_content + "\n", encoding="utf-8")

    console.print()
    console.print(Panel(
        f"[bold green]✓ 配置切换成功[/bold green]\n\n"
        f"  提供商: [cyan]{provider}[/cyan]\n"
        f"  模型:   [cyan]{model_name}[/cyan]\n"
        f"  工具:   [cyan]{tool}[/cyan]\n"
        f"  范围:   [cyan]{scope}[/cyan]\n"
        f"  写入:   [dim]{target_file}[/dim]"
        + (f"\n  认证:   [dim]{auth_file}[/dim]" if auth_file else ""),
        border_style="green",
        expand=False,
    ))


def _ensure_gitignore(claude_dir: Path) -> None:
    """确保 .claude/settings.local.json 被 .gitignore 忽略"""
    gitignore = claude_dir.parent / ".gitignore"
    entry = ".claude/settings.local.json"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        if entry not in content:
            gitignore.write_text(content.rstrip() + f"\n{entry}\n", encoding="utf-8")
    else:
        gitignore.write_text(f"{entry}\n", encoding="utf-8")


def _get_disabled_config_path(path: Path) -> Path:
    """返回配置文件对应的禁用文件名，如 settings.json.disabled / config.toml.disabled"""
    return path.with_name(f"{path.name}.disabled")


def _get_existing_config_backup_path(path: Path) -> Path:
    """返回恢复项目级配置时原有文件的备份路径，如 settings.json.bak / config.toml.bak"""
    return path.with_name(f"{path.name}.bak")


def _get_project_config_candidates(tool: str) -> list[dict]:
    """
    返回当前工作目录下所有项目级/项目本地配置文件的信息列表。
    每项: {label, path, disabled_path, is_active, is_disabled}
    """
    caller_dir = get_caller_dir()
    candidates: list[dict] = []

    if tool == "claude code":
        files = [
            ("项目级", caller_dir / ".claude" / "settings.json"),
            ("项目本地", caller_dir / ".claude" / "settings.local.json"),
        ]
    elif tool == "opencode":
        files = [
            ("项目级", caller_dir / "opencode.json"),
        ]
    elif tool == "codex":
        files = [
            ("项目级", caller_dir / ".codex" / "config.toml"),
        ]
    else:
        return []

    for label, path in files:
        disabled_path = _get_disabled_config_path(path)
        is_active = path.exists()
        is_disabled = disabled_path.exists()
        if is_active or is_disabled:
            candidates.append({
                "label": label,
                "path": path,
                "disabled_path": disabled_path,
                "is_active": is_active,
                "is_disabled": is_disabled,
            })

    return candidates


def disable_project_config(tool: str) -> None:
    """交互式选择并禁用（重命名为 *.disabled）项目级配置文件"""
    candidates = _get_project_config_candidates(tool)
    active = [c for c in candidates if c["is_active"]]

    if not active:
        console.print("[yellow]当前目录下没有可禁用的项目级配置文件。[/yellow]")
        return

    options = [
        f"{c['label']}  [dim]{c['path']}[/dim]"
        for c in active
    ]
    result, idx = pick_from_menu(
        options,
        "选择要禁用的配置文件  [dim](禁用后将回退到系统级配置)[/dim]",
        allow_back=True,
    )
    if result == "__BACK__":
        return

    chosen = active[idx - 1]
    src = chosen["path"]
    dst = chosen["disabled_path"]

    if dst.exists():
        dst.unlink()

    src.rename(dst)
    console.print()
    console.print(Panel(
        f"[bold green]✓ 已禁用配置文件[/bold green]\n\n"
        f"  原文件: [dim]{src}[/dim]\n"
        f"  已改名: [cyan]{dst.name}[/cyan]\n\n"
        f"  [dim]现在将回退到使用系统级配置。[/dim]\n"
        f"  [dim]如需恢复，请使用「重新启用配置」功能。[/dim]",
        border_style="green",
        expand=False,
    ))


def enable_project_config(tool: str) -> None:
    """交互式选择并重新启用（*.disabled → 原文件名）项目级配置文件"""
    candidates = _get_project_config_candidates(tool)
    disabled = [c for c in candidates if c["is_disabled"]]

    if not disabled:
        console.print("[yellow]当前目录下没有可重新启用的禁用配置文件。[/yellow]")
        return

    options = [
        f"{c['label']}  [dim]{c['disabled_path'].name}[/dim]"
        for c in disabled
    ]
    result, idx = pick_from_menu(
        options,
        "选择要重新启用的配置文件",
        allow_back=True,
    )
    if result == "__BACK__":
        return

    chosen = disabled[idx - 1]
    src = chosen["disabled_path"]
    dst = chosen["path"]

    if dst.exists():
        backup = _get_existing_config_backup_path(dst)
        dst.rename(backup)
        console.print(f"[dim]原有文件已备份为: {backup.name}[/dim]")

    src.rename(dst)
    console.print()
    console.print(Panel(
        f"[bold green]✓ 已重新启用配置文件[/bold green]\n\n"
        f"  已恢复: [cyan]{dst}[/cyan]\n\n"
        f"  [dim]项目级配置现已生效，优先于系统级配置。[/dim]",
        border_style="green",
        expand=False,
    ))


def resolve_action(tool: str) -> str:
    """
    让用户选择主操作：切换配置 / 禁用项目级配置 / 重新启用。
    返回 'switch' | 'disable' | 'enable' | '__BACK__'
    """
    caller_dir = get_caller_dir()
    candidates = _get_project_config_candidates(tool)
    has_active = any(c["is_active"] for c in candidates)
    has_disabled = any(c["is_disabled"] for c in candidates)

    options = ["🔄  切换配置（选择提供商 / API Key / 模型）"]
    action_map = {0: "switch"}

    if has_active:
        options.append("🚫  禁用项目级配置  [dim](改为 .disabled，回退到系统级)[/dim]")
        action_map[len(options) - 1] = "disable"

    if has_disabled:
        options.append("✅  重新启用项目级配置  [dim](从 .disabled 恢复)[/dim]")
        action_map[len(options) - 1] = "enable"

    result, choice = pick_from_menu(
        options,
        f"选择操作  [dim](工具: {tool}  目录: {caller_dir.name})[/dim]",
        allow_back=True,
    )
    if result == "__BACK__":
        return "__BACK__"

    return action_map[choice - 1]


# ──────────────────────────────────────────────
# CLI 入口
# ─────────────��────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """构建命令行解析器"""
    parser = argparse.ArgumentParser(description="AI Coding 配置切换器")
    parser.add_argument("-t", "--tool", help="工具名称（claude code / opencode / codex）")
    parser.add_argument("-p", "--provider", help="AI 服务提供商名称")
    parser.add_argument("-m", "--model", help="模型名称")
    parser.add_argument(
        "--scope",
        choices=["system", "project", "project-local"],
        help="配置写入范围: system / project / project-local",
    )
    parser.add_argument("--dry-run", action="store_true", help="只展示操作，不写入文件")
    parser.add_argument("--list-providers", action="store_true", help="列出所有可用提供商")
    parser.add_argument("--list-models", help="列出指定提供商下的所有模型")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # 确定工具（用于列表查询）
    tool = "claude code"
    if args.tool:
        normalized = normalize_tool_name(args.tool)
        if normalized and normalized in ["claude code", "opencode", "codex"]:
            tool = normalized

    # 纯列表查询，不显示 header
    if args.list_providers:
        providers = list_providers(tool)
        if not providers:
            console.print(f"[dim]工具 '{tool}' 暂无提供商配置[/dim]")
            return 0
        t = Table(title=f"可用提供商 [dim]({tool})[/dim]", box=rich_box.ROUNDED)
        t.add_column("提供商", style="cyan")
        t.add_column("模型数量", justify="right")
        for p in providers:
            t.add_row(p, str(len(list_models(p, tool))))
        console.print(t)
        return 0

    if args.list_models:
        models = list_models(args.list_models, tool)
        if not models:
            console.print(f"[dim]提供商 '{args.list_models}' 暂无模型[/dim]")
            return 0
        t = Table(title=f"提供商 '{args.list_models}' 的模型 [dim]({tool})[/dim]", box=rich_box.ROUNDED)
        t.add_column("模型名称", style="cyan")
        t.add_column("别名", style="dim")
        for m in models:
            alias = m.get("alias", "")
            t.add_row(m["name"], alias if alias != m["name"] else "")
        console.print(t)
        return 0

    print_header()

    try:
        # 确定工具
        if args.tool:
            normalized = normalize_tool_name(args.tool)
            if not normalized or normalized not in ["claude code", "opencode", "codex"]:
                raise ValueError(f"不支持的工具: {args.tool}。当前支持: claude code, opencode, codex")
            tool = normalized
        else:
            while True:
                tool = resolve_tool()
                # 选择操作（CLI 模式跳过，直接进入切换流程）
                action = resolve_action(tool)
                if action == "__BACK__":
                    # 返回工具选择
                    continue
                if action == "disable":
                    disable_project_config(tool)
                    return 0
                if action == "enable":
                    enable_project_config(tool)
                    return 0
                # action == "switch"：继续后续流程
                break

        # 确定写入范围（支持返回上一页）
        caller_dir = get_caller_dir()

        if tool == "opencode":
            scope_map = {
                "system": Path.home() / ".config" / "opencode" / "opencode.json",
                "project": caller_dir / "opencode.json",
            }
        elif tool == "codex":
            scope_map = {
                "system": Path.home() / ".codex" / "config.toml",
                "project": caller_dir / ".codex" / "config.toml",
            }
        else:
            scope_map = {
                "system": Path.home() / ".claude" / "settings.json",
                "project": caller_dir / ".claude" / "settings.json",
                "project-local": caller_dir / ".claude" / "settings.local.json",
            }

        if args.scope:
            if args.scope not in scope_map:
                supported_scopes = " / ".join(scope_map.keys())
                raise ValueError(f"工具 '{tool}' 不支持 scope={args.scope}，当前支持: {supported_scopes}")
            scope = args.scope
            target_file = scope_map[scope]
        else:
            while True:
                scope_result = resolve_scope(tool)
                if scope_result is not None:
                    scope, target_file = scope_result
                    break
                # 返回上一页（scope 页没有更上层，停在此处重选）

        # 确定提供商（支持返回上一页会退回 scope 选择）
        if args.provider:
            provider = args.provider
        else:
            while True:
                provider = resolve_provider(tool)
                if provider is None:
                    # 管理操作完成，重新选择提供商
                    continue
                if provider == "__BACK__":
                    # 返回 scope 选择
                    if not args.scope:
                        while True:
                            scope_result = resolve_scope(tool)
                            if scope_result is not None:
                                scope, target_file = scope_result
                                break
                    continue
                break

        # 确定 API Key（支持返回上一页回到提供商选择）
        # CLI 模式下跳过 API Key 选择，使用提供商默认 Key
        if args.provider:
            api_key = ""
        else:
            while True:
                api_key_result = resolve_api_key(provider, tool)
                if api_key_result is None:
                    # 管理操作完成，重新选择 API Key
                    continue
                if api_key_result == "__BACK__":
                    # 返回提供商选择
                    while True:
                        provider = resolve_provider(tool)
                        if provider is None:
                            continue
                        if provider == "__BACK__":
                            if not args.scope:
                                while True:
                                    scope_result = resolve_scope(tool)
                                    if scope_result is not None:
                                        scope, target_file = scope_result
                                        break
                            break
                        break
                    continue
                api_key = api_key_result
                break

        # 确定模型（支持返回上一页回到 API Key 选择）
        if args.model:
            model_name = args.model
        else:
            while True:
                model_name = resolve_model(provider, tool)
                if model_name is None:
                    # 管理操作完成，重新选择模型
                    continue
                if model_name == "__BACK__":
                    # 返回 API Key 选择
                    while True:
                        api_key_result = resolve_api_key(provider, tool)
                        if api_key_result is None:
                            continue
                        if api_key_result == "__BACK__":
                            break
                        api_key = api_key_result
                        break
                    if api_key_result == "__BACK__":
                        continue
                    continue
                break

        switch_config(
            provider=provider,
            model_name=model_name,
            dry_run=args.dry_run,
            scope=scope,
            target_file=target_file,
            tool=tool,
            api_key=api_key,
        )
        return 0

    except KeyboardInterrupt:
        console.print("\n[dim]已取消。[/dim]")
        return 130
    except Exception as exc:
        Console(stderr=True).print(f"[red]错误: {exc}[/red]")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
