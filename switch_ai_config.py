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

# 导入 ProviderManager
import importlib.util
cli_spec = importlib.util.spec_from_file_location("ai_config_cli", PROJECT_ROOT / "ai-config-cli.py")
cli_module = importlib.util.module_from_spec(cli_spec)
cli_spec.loader.exec_module(cli_module)
ProviderManager = cli_module.ProviderManager


def get_caller_dir() -> Path:
    """获取用户调用脚本时所在的目录（通过 shell 脚本传入 CALLER_DIR 环境变量）"""
    caller = os.environ.get("CALLER_DIR")
    if caller:
        return Path(caller)
    return Path.cwd()


def list_providers() -> list[str]:
    """列出所有提供商"""
    if not CLAUDE_CODE_CONFIG_DIR.exists():
        return []
    providers = []
    for p in CLAUDE_CODE_CONFIG_DIR.iterdir():
        if p.is_dir() and not p.name.startswith('.'):
            providers.append(p.name)
    return sorted(providers)


def list_models(provider: str) -> list[dict]:
    """列出提供商下的所有模型"""
    config_file = CLAUDE_CODE_CONFIG_DIR / provider / "config.json"
    if not config_file.exists():
        return []
    config = json.loads(config_file.read_text(encoding="utf-8"))
    return config.get("models", [])


def get_provider_config(provider: str) -> dict:
    """获取提供商配置"""
    config_file = CLAUDE_CODE_CONFIG_DIR / provider / "config.json"
    if not config_file.exists():
        return {"api_url": "", "api_key": "", "models": []}
    return json.loads(config_file.read_text(encoding="utf-8"))


def get_global_settings() -> dict:
    """读取全局配置文件 global_settings.json"""
    global_settings_file = CLAUDE_CODE_CONFIG_DIR / "global_settings.json"
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


def generate_settings(provider: str, model_name: str) -> dict:
    """生成Claude Code的settings.json配置（包含 env、permissions、hooks 等）"""
    config = get_provider_config(provider)

    model_exists = any(m["name"] == model_name for m in config.get("models", []))
    if not model_exists:
        raise ValueError(f"模型 '{model_name}' 不存在于提供商 '{provider}'")

    global_settings = get_global_settings()

    env_settings: dict = {"env": {}}
    if config.get("api_key"):
        env_settings["env"]["ANTHROPIC_AUTH_TOKEN"] = config["api_key"]
    if config.get("api_url"):
        env_settings["env"]["ANTHROPIC_BASE_URL"] = config["api_url"]

    env_settings["env"]["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    env_settings["env"]["API_TIMEOUT_MS"] = "600000"
    env_settings["env"]["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model_name

    settings = deep_merge(env_settings, global_settings)
    return settings


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
) -> tuple[str, int]:
    """从菜单中选择，返回 (选项名, 选项索引)"""
    all_options = list(options)
    extra_start_idx = len(all_options)
    if extra_options:
        all_options.extend(extra_options)

    if not all_options:
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

        if allow_open_folder and folder_path:
            table.add_row("[dim]0[/dim]", "[dim]📂  打开配置文件夹（访达）[/dim]")

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

        raw = Prompt.ask("[cyan]请输入编号[/cyan]").strip()
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
    return ["claude code", "opencode"]


# ──────────────────────────────────────────────
# 交互式管理操作
# ──────────────────────────────────────────────

def interactive_add_provider() -> str:
    """交互式添加提供商"""
    console.print(Panel("[bold]添加新提供商[/bold]", border_style="green", expand=False))

    name = Prompt.ask("  提供商名称").strip()
    if not name:
        console.print("[red]提供商名称不能为空[/red]")
        return ""

    if (CLAUDE_CODE_CONFIG_DIR / name).exists():
        console.print(f"[yellow]提供商 '{name}' 已存在[/yellow]")
        return name

    api_url = Prompt.ask("  API URL [dim](留空跳过)[/dim]", default="").strip()
    api_key = Prompt.ask("  API Key [dim](留空跳过)[/dim]", default="", password=True).strip()

    manager = ProviderManager()
    manager.add_provider(name, api_url, api_key)
    console.print(f"[green]✓ 已添加提供商:[/green] {name}")
    return name


def interactive_edit_provider(provider: str) -> None:
    """交互式编辑提供商"""
    console.print(Panel(f"[bold]编辑提供商:[/bold] {provider}", border_style="yellow", expand=False))

    manager = ProviderManager()
    config = manager.get_provider_config(provider)

    current_url = config.get("api_url", "")
    current_key = config.get("api_key", "")

    new_url = Prompt.ask(f"  API URL", default=current_url).strip()
    new_key = Prompt.ask(
        f"  API Key [dim](留空保持不变)[/dim]",
        default="",
        password=True,
    ).strip()

    changed = False
    if new_url != current_url:
        manager.set_provider_config(provider, api_url=new_url)
        changed = True
    if new_key:
        manager.set_provider_config(provider, api_key=new_key)
        changed = True

    console.print("[green]✓ 已更新配置[/green]" if changed else "[dim]未做任何修改[/dim]")


def interactive_add_model(provider: str) -> str:
    """交互式添加模型，返回模型名称"""
    console.print(Panel(f"[bold]添加模型到:[/bold] {provider}", border_style="green", expand=False))

    model_name = Prompt.ask("  模型名称").strip()
    if not model_name:
        console.print("[red]模型名称不能为空[/red]")
        return ""

    alias = Prompt.ask(f"  别名 [dim](留空使用模型名)[/dim]", default="").strip()

    manager = ProviderManager()
    try:
        manager.add_model(provider, model_name, alias)
        console.print(f"[green]✓ 已添加模型:[/green] {model_name}")
    except ValueError as e:
        console.print(f"[red]错误: {e}[/red]")

    return model_name


def interactive_delete_provider(provider: str) -> bool:
    """交互式删除提供商"""
    if Confirm.ask(f"  [yellow]确定要删除提供商 '{provider}' 吗？[/yellow]", default=False):
        manager = ProviderManager()
        manager.remove_provider(provider)
        console.print(f"[green]✓ 已删除提供商:[/green] {provider}")
        return True
    return False


def interactive_delete_model(provider: str, model_name: str) -> bool:
    """交互式删除模型"""
    if Confirm.ask(f"  [yellow]确定要删除模型 '{model_name}' 吗？[/yellow]", default=False):
        manager = ProviderManager()
        manager.remove_model(provider, model_name)
        console.print(f"[green]✓ 已删除模型:[/green] {model_name}")
        return True
    return False


# ──────────────────────────────────────────────
# 交互式选择流程
# ──────────��───────────────────────────────────

def resolve_tool() -> str:
    """交互式选择工具"""
    tools = list_tools()
    result, _ = pick_from_menu(tools, "选择目标 AI Coding 工具")
    return result


def resolve_scope() -> tuple[str, Path]:
    """交互式选择写入范围，返回 (scope_name, target_file)"""
    caller_dir = get_caller_dir()

    scope_options = [
        f"系统级  [dim](~/.claude/settings.json — 对所有项目生效)[/dim]",
        f"项目级  [dim]({caller_dir / '.claude/settings.json'} — 仅当前项目，可提交 Git)[/dim]",
        f"项目本地 [dim]({caller_dir / '.claude/settings.local.json'} — 仅当前项目，不提交 Git)[/dim]",
    ]
    result, choice = pick_from_menu(scope_options, "选择配置写入范围")

    if choice == 1:
        return "system", Path.home() / ".claude" / "settings.json"
    elif choice == 2:
        return "project", caller_dir / ".claude" / "settings.json"
    else:
        return "project-local", caller_dir / ".claude" / "settings.local.json"


def resolve_provider(tool: str) -> str | None:
    """交互式选择提供商，返回 None 表示需要重新选择"""
    providers = list_providers()

    extra_options = [
        "+ 添加新提供商",
        "+ 编辑提供商配置",
        "+ 删除提供商",
    ]

    if not providers:
        result, _ = pick_from_menu(
            [], f"选择 AI 服务提供商  [dim](工具: {tool})[/dim]",
            extra_options=["+ 添加新提供商"],
        )
        if "+ 添加新提供商" in result:
            name = interactive_add_provider()
            return name or None
        return None

    result, choice = pick_from_menu(
        providers,
        f"选择 AI 服务提供商  [dim](工具: {tool})[/dim]",
        allow_open_folder=True,
        folder_path=CLAUDE_CODE_CONFIG_DIR,
        extra_options=extra_options,
    )

    if result == "+ 添加新提供商":
        name = interactive_add_provider()
        return name or None
    elif result == "+ 编辑提供商配置":
        if providers:
            selected, _ = pick_from_menu(providers, "选择要编辑的提供商")
            interactive_edit_provider(selected)
        return None
    elif result == "+ 删除提供商":
        if providers:
            selected, _ = pick_from_menu(providers, "选择要删除的提供商")
            interactive_delete_provider(selected)
        return None

    return result


def resolve_model(provider: str) -> str | None:
    """交互式选择模型，返回 None 表示需要重新选择"""
    models = list_models(provider)

    extra_options = [
        "+ 添加新模型",
        "+ 编辑模型别名",
        "+ 删除模型",
    ]

    if not models:
        result, _ = pick_from_menu(
            [], f"选择模型  [dim](提供商: {provider})[/dim]",
            extra_options=["+ 添加新模型"],
        )
        if "+ 添加新模型" in result:
            interactive_add_model(provider)
            models = list_models(provider)
            if not models:
                return None
        # 重新进入完整选择流程
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
    )

    if result == "+ 添加新模型":
        interactive_add_model(provider)
        return None
    elif result == "+ 编辑模型别名":
        if models:
            sel, _ = pick_from_menu(model_options, "选择要编辑的模型")
            model_name = models[model_options.index(sel)]["name"]
            model_info = next((m for m in models if m["name"] == model_name), None)
            if model_info:
                new_alias = Prompt.ask(
                    f"  新别名", default=model_info.get("alias", model_name)
                ).strip()
                if new_alias:
                    manager = ProviderManager()
                    config = manager.get_provider_config(provider)
                    for m in config.get("models", []):
                        if m["name"] == model_name:
                            m["alias"] = new_alias
                            break
                    manager._save_provider_config(provider, config)
                    console.print(f"[green]✓ 已更新别名:[/green] {new_alias}")
        return None
    elif result == "+ 删除模型":
        if models:
            sel, _ = pick_from_menu(model_options, "选择要删除的模型")
            model_name = models[model_options.index(sel)]["name"]
            interactive_delete_model(provider, model_name)
        return None

    # 提取真实模型名（去掉 rich markup）
    idx = model_options.index(result)
    return models[idx]["name"]


# ──────────────────────────────────────────────
# 核心切换逻辑
# ──────────────────────────────────────────────

def switch_config(provider: str, model_name: str, dry_run: bool, scope: str, target_file: Path) -> None:
    """切换配置"""
    backup_file = CLAUDE_CODE_CONFIG_DIR / provider / f"settings.{scope}.bak"

    settings = generate_settings(provider, model_name)
    settings_data = json.dumps(settings, indent=2, ensure_ascii=False).encode("utf-8")

    if dry_run:
        console.print()
        console.print(Panel(
            f"[bold cyan]Dry Run 预览[/bold cyan]\n\n"
            f"  提供商: [yellow]{provider}[/yellow]\n"
            f"  模型:   [yellow]{model_name}[/yellow]\n"
            f"  范围:   [yellow]{scope}[/yellow]\n"
            f"  目标:   [dim]{target_file}[/dim]"
            + (f"\n  备份:   [dim]{backup_file}[/dim]" if target_file.exists() else ""),
            border_style="cyan",
            expand=False,
        ))
        console.print()
        console.print(Panel(
            json.dumps(settings, indent=2, ensure_ascii=False),
            title="[bold]配置内容预览[/bold]",
            border_style="bright_black",
        ))
        return

    target_file.parent.mkdir(parents=True, exist_ok=True)
    backup_file.parent.mkdir(parents=True, exist_ok=True)

    if target_file.exists():
        shutil.copy2(target_file, backup_file)
        console.print(f"[dim]已备份当前配置: {backup_file}[/dim]")

    if scope == "project-local":
        _ensure_gitignore(target_file.parent)

    target_file.write_bytes(settings_data)

    console.print()
    console.print(Panel(
        f"[bold green]✓ 配置切换成功[/bold green]\n\n"
        f"  提供商: [cyan]{provider}[/cyan]\n"
        f"  模型:   [cyan]{model_name}[/cyan]\n"
        f"  范围:   [cyan]{scope}[/cyan]\n"
        f"  写入:   [dim]{target_file}[/dim]",
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


# ──────────────────────────────────────────────
# CLI 入口
# ─────────────��────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """构建命令行解析器"""
    parser = argparse.ArgumentParser(description="AI Coding 配置切换器")
    parser.add_argument("-t", "--tool", help="工具名称（claude code / opencode）")
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

    # 纯列表查询，不显示 header
    if args.list_providers:
        providers = list_providers()
        if not providers:
            console.print("[dim]暂无提供商配置[/dim]")
            return 0
        t = Table(title="可用提供商", box=rich_box.ROUNDED)
        t.add_column("提供商", style="cyan")
        t.add_column("模型数量", justify="right")
        for p in providers:
            t.add_row(p, str(len(list_models(p))))
        console.print(t)
        return 0

    if args.list_models:
        models = list_models(args.list_models)
        if not models:
            console.print(f"[dim]提供商 '{args.list_models}' 暂无模型[/dim]")
            return 0
        t = Table(title=f"提供商 '{args.list_models}' 的模型", box=rich_box.ROUNDED)
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
            if not normalized or normalized not in ["claude code", "opencode"]:
                raise ValueError(f"不支持的工具: {args.tool}。当前支持: claude code, opencode")
            tool = normalized
        else:
            tool = resolve_tool()

        # 确定写入范围
        caller_dir = get_caller_dir()
        scope_map = {
            "system": Path.home() / ".claude" / "settings.json",
            "project": caller_dir / ".claude" / "settings.json",
            "project-local": caller_dir / ".claude" / "settings.local.json",
        }
        if args.scope:
            scope = args.scope
            target_file = scope_map[scope]
        else:
            scope, target_file = resolve_scope()

        # 确定提供商
        while True:
            provider = args.provider if args.provider else resolve_provider(tool)
            if provider:
                break
            if args.provider:
                raise ValueError("提供商不存在")

        # 确定模型
        while True:
            model_name = args.model if args.model else resolve_model(provider)
            if model_name:
                break
            if args.model:
                raise ValueError("模型不存在")

        switch_config(
            provider=provider,
            model_name=model_name,
            dry_run=args.dry_run,
            scope=scope,
            target_file=target_file,
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
