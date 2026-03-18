#!/usr/bin/env python3
"""
AI Coding 配置切换器 - 配置切换模块
支持两级目录结构：提供商 -> 模型
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
CLAUDE_CODE_CONFIG_DIR = PROJECT_ROOT / "configs" / "claude_code"

# 导入 ProviderManager
import importlib.util
cli_spec = importlib.util.spec_from_file_location("ai_config_cli", PROJECT_ROOT / "ai-config-cli.py")
cli_module = importlib.util.module_from_spec(cli_spec)
cli_spec.loader.exec_module(cli_module)
ProviderManager = cli_module.ProviderManager


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


def generate_settings(provider: str, model_name: str) -> dict:
    """生成Claude Code的settings.json配置"""
    config = get_provider_config(provider)

    # 验证模型存在
    model_exists = any(m["name"] == model_name for m in config.get("models", []))
    if not model_exists:
        raise ValueError(f"模型 '{model_name}' 不存在于提供商 '{provider}'")

    settings = {"env": {}}

    if config.get("api_key"):
        settings["env"]["ANTHROPIC_AUTH_TOKEN"] = config["api_key"]
    if config.get("api_url"):
        settings["env"]["ANTHROPIC_BASE_URL"] = config["api_url"]

    settings["env"]["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
    settings["env"]["API_TIMEOUT_MS"] = "600000"
    settings["env"]["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model_name

    return settings


def list_candidate_files(config_dir: Path) -> list[Path]:
    """列出配置目录下的候选文件（旧版兼容）"""
    if not config_dir.exists():
        return []
    files = []
    for p in config_dir.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() in {".json", ".bak"}:
            files.append(p)
    return sorted(files, key=lambda p: p.name.lower())


def pick_from_menu(options: list[str], title: str, allow_open_folder: bool = False, folder_path: Path | None = None, extra_options: list[str] | None = None) -> tuple[str, int]:
    """从菜单中选择，返回 (选项名, 选项索引)"""
    all_options = list(options)
    extra_start_idx = len(all_options)

    if extra_options:
        all_options.extend(extra_options)

    if not all_options:
        raise ValueError("没有可选项")

    print(f"\n{title}")

    if allow_open_folder and folder_path:
        print(f"  0. 打开配置文件夹（访达）")

    # 显示常规选项
    for idx, item in enumerate(options, start=1):
        print(f"  {idx}. {item}")

    # 显示额外选项
    if extra_options:
        print()  # 空行分隔
        for idx, item in enumerate(extra_options, start=extra_start_idx + 1):
            print(f"  {idx}. {item}")

    while True:
        raw = input("请输入编号: ").strip()
        if not raw.isdigit():
            print("输入无效，请输入数字编号。")
            continue
        choice = int(raw)

        if choice == 0 and allow_open_folder and folder_path:
            open_folder_in_finder(folder_path)
            print(f"\n已在访达中打开: {folder_path}")
            print("请选择:")
            continue

        if 1 <= choice <= len(all_options):
            return all_options[choice - 1], choice
        print("编号超出范围，请重新输入。")


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
        print(f"警告: 无法打开文件夹: {e}", file=sys.stderr)


def list_tools() -> list[str]:
    """列出所有支持的工具"""
    return ["claude code", "opencode"]


def interactive_add_provider() -> str:
    """交互式添加提供商"""
    print("\n" + "=" * 40)
    print("添加新提供商")
    print("=" * 40)

    name = input("提供商名称: ").strip()
    if not name:
        print("提供商名称不能为空")
        return ""

    if (CLAUDE_CODE_CONFIG_DIR / name).exists():
        print(f"提供商 '{name}' 已存在")
        return name

    api_url = input("API URL (留空跳过): ").strip()
    api_key = input("API Key (留空跳过): ").strip()

    manager = ProviderManager()
    manager.add_provider(name, api_url, api_key)

    return name


def interactive_edit_provider(provider: str) -> None:
    """交互式编辑提供商"""
    print("\n" + "=" * 40)
    print(f"编辑提供商: {provider}")
    print("=" * 40)

    manager = ProviderManager()
    config = manager.get_provider_config(provider)

    current_url = config.get("api_url", "")
    current_key = config.get("api_key", "")

    new_url = input(f"API URL [{current_url}]: ").strip()
    new_key = input(f"API Key [{current_key[:8] if current_key else ''}...]: ").strip()

    if new_url or new_key:
        manager.set_provider_config(provider, new_url or None, new_key or None)
        print("✓ 已更新配置")
    else:
        print("未做任何修改")


def interactive_add_model(provider: str) -> str:
    """交互式添加模型，返回模型名称"""
    print("\n" + "=" * 40)
    print(f"添加模型到: {provider}")
    print("=" * 40)

    model_name = input("模型名称: ").strip()
    if not model_name:
        print("模型名称不能为空")
        return ""

    alias = input(f"别名 (留空使用模型名): ").strip()

    manager = ProviderManager()
    try:
        manager.add_model(provider, model_name, alias)
    except ValueError as e:
        print(f"错误: {e}")

    return model_name


def interactive_delete_provider(provider: str) -> bool:
    """交互式删除提供商"""
    confirm = input(f"确定要删除提供商 '{provider}' 吗？(y/N): ").strip().lower()
    if confirm == 'y':
        manager = ProviderManager()
        manager.remove_provider(provider)
        return True
    return False


def interactive_delete_model(provider: str, model_name: str) -> bool:
    """交互式删除模型"""
    confirm = input(f"确定要删除模型 '{model_name}' 吗？(y/N): ").strip().lower()
    if confirm == 'y':
        manager = ProviderManager()
        manager.remove_model(provider, model_name)
        return True
    return False


def resolve_tool() -> str:
    """交互式选择工具"""
    tools = list_tools()
    result, _ = pick_from_menu(tools, "请选择目标 AI Coding 工具:")
    return result


def resolve_provider(tool: str) -> str | None:
    """交互式选择提供商，返回 None 表示返回上级菜单"""
    providers = list_providers()

    extra_options = [
        "+ 添加新提供商",
        "+ 编辑提供商配置",
        "+ 删除提供商"
    ]

    if not providers:
        # 没有提供商时只显示添加选项
        result, choice = pick_from_menu([], f"请选择 AI 服务提供商 (工具: {tool}):",
                                        extra_options=["+ 添加新提供商"])
        if "+ 添加新提供商" in result:
            name = interactive_add_provider()
            if name:
                return name
            return None
        return None

    result, choice = pick_from_menu(providers, f"请选择 AI 服务提供商 (工具: {tool}):",
                                    allow_open_folder=True, folder_path=CLAUDE_CODE_CONFIG_DIR,
                                    extra_options=extra_options)

    if result == "+ 添加新提供商":
        name = interactive_add_provider()
        if name:
            return name
        return None
    elif result == "+ 编辑提供商配置":
        if providers:
            # 让用户选择要编辑的提供商
            selected, _ = pick_from_menu(providers, "选择要编辑的提供商:")
            interactive_edit_provider(selected)
        return None  # 返回重新选择
    elif result == "+ 删除提供商":
        if providers:
            selected, _ = pick_from_menu(providers, "选择要删除的提供商:")
            if interactive_delete_provider(selected):
                return None  # 返回重新选择
        return None

    return result


def resolve_model(provider: str) -> str | None:
    """交互式选择模型，返回 None 表示返回上级菜单"""
    models = list_models(provider)

    extra_options = [
        "+ 添加新模型",
        "+ 编辑模型",
        "+ 删除模型"
    ]

    if not models:
        # 没有模型时只显示添加选项
        result, _ = pick_from_menu([], f"请选择模型 (提供商: {provider}):",
                                   extra_options=["+ 添加新模型"])
        if "+ 添加新模型" in result:
            interactive_add_model(provider)
            # 添加后重新获取模型列表
            models = list_models(provider)
            if not models:
                return None

    model_options = [f"{m['name']} ({m.get('alias', m['name'])})" for m in models]

    result, choice = pick_from_menu(model_options, f"请选择模型 (提供商: {provider}):",
                                    extra_options=extra_options)

    if result == "+ 添加新模型":
        interactive_add_model(provider)
        return None  # 返回重新选择
    elif result == "+ 编辑模型":
        if models:
            selected, _ = pick_from_menu([f"{m['name']} ({m.get('alias', m['name'])})" for m in models],
                                        "选择要编辑的模型:")
            # 提取模型名称
            model_name = selected.split(" ")[0]
            # 让用户编辑别名
            model_info = next((m for m in models if m["name"] == model_name), None)
            if model_info:
                new_alias = input(f"新别名 [{model_info.get('alias', model_name)}]: ").strip()
                if new_alias:
                    manager = ProviderManager()
                    config = manager.get_provider_config(provider)
                    for m in config.get("models", []):
                        if m["name"] == model_name:
                            m["alias"] = new_alias
                            break
                    manager._save_provider_config(provider, config)
                    print("✓ 已更新别名")
        return None
    elif result == "+ 删除模型":
        if models:
            selected, _ = pick_from_menu([f"{m['name']} ({m.get('alias', m['name'])})" for m in models],
                                        "选择要删除的模型:")
            model_name = selected.split(" ")[0]
            if interactive_delete_model(provider, model_name):
                return None
        return None

    # 提取模型名称
    return result.split(" ")[0]


def resolve_config_file(config_arg: str | None, config_dir: Path) -> Path:
    """解析配置文件（旧版兼容）"""
    candidates = list_candidate_files(config_dir)
    if not candidates:
        raise ValueError(f"在 {config_dir} 下没有找到可用配置文件（.json 或 .bak）")

    if config_arg:
        selected = (config_dir / config_arg).resolve()
        valid = {p.resolve() for p in candidates}
        if selected not in valid:
            names = ", ".join(p.name for p in candidates)
            raise ValueError(f"未找到配置文件: {config_arg}。可选: {names}")
        return selected

    names = [p.name for p in candidates]
    chosen_name = pick_from_menu(names, f"请选择要载入的配置文件:", allow_open_folder=True, folder_path=config_dir)
    return config_dir / chosen_name


def switch_config(provider: str, model_name: str, dry_run: bool) -> None:
    """切换配置"""
    target_file = Path.home() / ".claude" / "settings.json"
    backup_file = CLAUDE_CODE_CONFIG_DIR / provider / "settings.json.bak"

    # 生成配置
    settings = generate_settings(provider, model_name)
    settings_data = json.dumps(settings, indent=2, ensure_ascii=False).encode("utf-8")

    if dry_run:
        print("\n[Dry Run] 将执行以下操作:")
        if target_file.exists():
            print(f"  1) 备份: {target_file} -> {backup_file}")
        else:
            print(f"  1) 跳过备份: 目标文件不存在")
        print(f"  2) 切换: {provider} / {model_name} -> {target_file}")
        print("\n配置预览:")
        print(json.dumps(settings, indent=2, ensure_ascii=False))
        return

    target_file.parent.mkdir(parents=True, exist_ok=True)
    backup_file.parent.mkdir(parents=True, exist_ok=True)

    if target_file.exists():
        shutil.copy2(target_file, backup_file)
        print(f"已备份当前配置到: {backup_file}")

    target_file.write_bytes(settings_data)
    print(f"已切换配置: {provider} / {model_name} -> {target_file}")


def build_parser() -> argparse.ArgumentParser:
    """构建命令行解析器"""
    parser = argparse.ArgumentParser(
        description="AI Coding 配置切换器"
    )
    parser.add_argument(
        "-t", "--tool",
        help="工具名称（当前仅支持 claude code）",
    )
    parser.add_argument(
        "-p", "--provider",
        help="AI 服务提供商名称",
    )
    parser.add_argument(
        "-m", "--model",
        help="模型名称",
    )
    parser.add_argument(
        "-c", "--config",
        help="配置文件名（旧版兼容，相对于工具配置目录）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只展示操作，不写入文件",
    )
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="列出所有可用的提供商",
    )
    parser.add_argument(
        "--list-models",
        help="列出指定提供商下的所有模型",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # 处理列表命令
    if args.list_providers:
        providers = list_providers()
        if not providers:
            print("暂无提供商配置")
            return 0
        print(f"可用的提供商 ({len(providers)}):")
        for p in providers:
            models = list_models(p)
            print(f"  • {p} ({len(models)} 个模型)")
        return 0

    if args.list_models:
        models = list_models(args.list_models)
        if not models:
            print(f"提供商 '{args.list_models}' 暂无模型")
            return 0
        print(f"提供商 '{args.list_models}' 的模型 ({len(models)}):")
        for m in models:
            alias = f" -> {m.get('alias')}" if m.get('alias') != m['name'] else ""
            print(f"  • {m['name']}{alias}")
        return 0

    try:
        # 确定工具
        if args.tool:
            normalized = normalize_tool_name(args.tool)
            if not normalized or normalized not in ["claude code", "opencode"]:
                raise ValueError(f"不支持的工具: {args.tool}。当前支持: claude code, opencode")
            tool = normalized
        else:
            tool = resolve_tool()

        # 确定提供商（可能需要多次选择，因为编辑后要重新选择）
        while True:
            provider = args.provider if args.provider else resolve_provider(tool)
            if provider:
                break
            if not args.provider:
                # 用户取消编辑，返回继续选择
                continue
            else:
                raise ValueError("提供商不存在")

        # 确定模型（可能需要多次选择）
        while True:
            model_name = args.model if args.model else resolve_model(provider)
            if model_name:
                break
            if not args.model:
                continue
            else:
                raise ValueError("模型不存在")

        switch_config(provider=provider, model_name=model_name, dry_run=args.dry_run)
        return 0

    except KeyboardInterrupt:
        print("\n已取消。")
        return 130
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
