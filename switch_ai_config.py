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


def pick_from_menu(options: list[str], title: str, allow_open_folder: bool = False, folder_path: Path | None = None) -> str:
    """从菜单中选择"""
    if not options:
        raise ValueError("没有可选项")
    print(f"\n{title}")

    if allow_open_folder and folder_path:
        print(f"  0. 打开配置文件夹（访达）")

    for idx, item in enumerate(options, start=1):
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

        if 1 <= choice <= len(options):
            return options[choice - 1]
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


def resolve_tool() -> str:
    """交互式选择工具"""
    tools = list_tools()
    return pick_from_menu(tools, "请选择目标 AI Coding 工具:")


def resolve_provider(tool: str) -> str:
    """交互式选择提供商"""
    providers = list_providers()

    if not providers:
        print("错误: 未找到任何提供商配置", file=sys.stderr)
        print(f"请使用 'ai-config-cli.py add-provider' 命令添加提供商", file=sys.stderr)
        raise ValueError("没有可用的提供商")

    return pick_from_menu(providers, f"请选择 AI 服务提供商 (工具: {tool}):", allow_open_folder=True, folder_path=CLAUDE_CODE_CONFIG_DIR)


def resolve_model(provider: str) -> str:
    """交互式选择模型"""
    models = list_models(provider)

    if not models:
        print(f"错误: 提供商 '{provider}' 下没有配置任何模型", file=sys.stderr)
        print(f"请使用 'ai-config-cli.py add-model {provider} <模型名>' 添加模型", file=sys.stderr)
        raise ValueError(f"提供商 '{provider}' 没有可用的模型")

    model_options = [f"{m['name']} ({m.get('alias', m['name'])})" for m in models]
    selected = pick_from_menu(model_options, f"请选择模型 (提供商: {provider}):")
    # 提取模型名称
    return selected.split(" ")[0]


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

        # 确定提供商
        if args.provider:
            providers = list_providers()
            if args.provider not in providers:
                raise ValueError(f"提供商 '{args.provider}' 不存在。可用: {', '.join(providers)}")
            provider = args.provider
        else:
            provider = resolve_provider(tool)

        # 确定模型
        if args.model:
            models = list_models(provider)
            model_names = [m["name"] for m in models]
            if args.model not in model_names:
                raise ValueError(f"模型 '{args.model}' 不存在。可用: {', '.join(model_names)}")
            model_name = args.model
        else:
            model_name = resolve_model(provider)

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
