#!/usr/bin/env python3
"""
AI Coding 配置切换器 - 管理工具
用于管理提供商和模型配置
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
CLAUDE_CODE_CONFIG_DIR = PROJECT_ROOT / "configs" / "claude_code"


class ProviderManager:
    """提供商管理器"""

    def __init__(self, config_dir: Path = CLAUDE_CODE_CONFIG_DIR):
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def list_providers(self) -> list[str]:
        """列出所有提供商"""
        if not self.config_dir.exists():
            return []
        providers = []
        for p in self.config_dir.iterdir():
            if p.is_dir() and not p.name.startswith('.'):
                providers.append(p.name)
        return sorted(providers)

    def provider_exists(self, name: str) -> bool:
        """检查提供商是否存在"""
        return (self.config_dir / name).is_dir()

    def get_provider_dir(self, name: str) -> Path:
        """获取提供商目录"""
        return self.config_dir / name

    def add_provider(self, name: str, api_url: str = "", api_key: str = "") -> None:
        """添加提供商"""
        if self.provider_exists(name):
            raise ValueError(f"提供商 '{name}' 已存在")

        provider_dir = self.config_dir / name
        provider_dir.mkdir(parents=True, exist_ok=True)

        # 创建配置信息文件
        config_info = {
            "api_url": api_url,
            "api_key": api_key,
            "models": []
        }
        self._save_provider_config(name, config_info)
        print(f"✓ 已添加提供商: {name}")

    def remove_provider(self, name: str) -> None:
        """删除提供商"""
        import shutil

        if not self.provider_exists(name):
            raise ValueError(f"提供商 '{name}' 不存在")

        provider_dir = self.config_dir / name
        shutil.rmtree(provider_dir)
        print(f"✓ 已删除提供商: {name}")

    def get_provider_config(self, name: str) -> dict:
        """获取提供商配置"""
        config_file = self.config_dir / name / "config.json"
        if not config_file.exists():
            return {"api_url": "", "api_key": "", "models": []}
        return json.loads(config_file.read_text(encoding="utf-8"))

    def _save_provider_config(self, name: str, config: dict) -> None:
        """保存提供商配置"""
        config_file = self.config_dir / name / "config.json"
        config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    def set_provider_config(self, name: str, api_url: str = None, api_key: str = None) -> None:
        """设置提供商配置"""
        if not self.provider_exists(name):
            raise ValueError(f"提供商 '{name}' 不存在")

        config = self.get_provider_config(name)

        if api_url is not None:
            config["api_url"] = api_url
        if api_key is not None:
            config["api_key"] = api_key

        self._save_provider_config(name, config)
        print(f"✓ 已更新提供商配置: {name}")

    def add_model(self, provider: str, model_name: str, alias: str = "") -> None:
        """添加模型"""
        if not self.provider_exists(provider):
            raise ValueError(f"提供商 '{provider}' 不存在")

        config = self.get_provider_config(provider)

        # 检查模型是否已存在
        for model in config.get("models", []):
            if model["name"] == model_name:
                raise ValueError(f"模型 '{model_name}' 已存在于提供商 '{provider}'")

        model_info = {
            "name": model_name,
            "alias": alias or model_name
        }
        config.setdefault("models", []).append(model_info)
        self._save_provider_config(provider, config)
        print(f"✓ 已添加模型: {model_name} -> {provider}")

    def remove_model(self, provider: str, model_name: str) -> None:
        """删除模型"""
        if not self.provider_exists(provider):
            raise ValueError(f"提供商 '{provider}' 不存在")

        config = self.get_provider_config(provider)
        models = config.get("models", [])

        original_count = len(models)
        config["models"] = [m for m in models if m["name"] != model_name]

        if len(config["models"]) == original_count:
            raise ValueError(f"模型 '{model_name}' 不存在于提供商 '{provider}'")

        self._save_provider_config(provider, config)
        print(f"✓ 已删除模型: {model_name} <- {provider}")

    def list_models(self, provider: str) -> list[dict]:
        """列出提供商下的所有模型"""
        if not self.provider_exists(provider):
            raise ValueError(f"提供商 '{provider}' 不存在")

        config = self.get_provider_config(provider)
        return config.get("models", [])

    def generate_settings_file(self, provider: str, model_name: str) -> dict:
        """生成Claude Code的settings.json配置"""
        if not self.provider_exists(provider):
            raise ValueError(f"提供商 '{provider}' 不存在")

        config = self.get_provider_config(provider)

        # 查找模型
        model_info = None
        for m in config.get("models", []):
            if m["name"] == model_name:
                model_info = m
                break

        if model_info is None:
            raise ValueError(f"模型 '{model_name}' 不存在于提供商 '{provider}'")

        # 构建settings配置
        settings = {
            "env": {}
        }

        if config.get("api_key"):
            settings["env"]["ANTHROPIC_AUTH_TOKEN"] = config["api_key"]
        if config.get("api_url"):
            settings["env"]["ANTHROPIC_BASE_URL"] = config["api_url"]

        settings["env"]["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
        settings["env"]["API_TIMEOUT_MS"] = "600000"
        settings["env"]["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model_name

        return settings


def cmd_add_provider(args: argparse.Namespace) -> int:
    """添加提供商命令"""
    manager = ProviderManager()
    try:
        manager.add_provider(args.name, args.api_url, args.api_key)
        return 0
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_remove_provider(args: argparse.Namespace) -> int:
    """删除提供商命令"""
    manager = ProviderManager()
    try:
        manager.remove_provider(args.name)
        return 0
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_list_providers(args: argparse.Namespace) -> int:
    """列出所有提供商"""
    manager = ProviderManager()
    providers = manager.list_providers()

    if not providers:
        print("暂无提供商，请使用 'add-provider' 命令添加")
        return 0

    print(f"共有 {len(providers)} 个提供商:\n")
    for name in providers:
        config = manager.get_provider_config(name)
        model_count = len(config.get("models", []))
        print(f"  • {name} ({model_count} 个模型)")
    return 0


def cmd_add_model(args: argparse.Namespace) -> int:
    """添加模型命令"""
    manager = ProviderManager()
    try:
        manager.add_model(args.provider, args.name, args.alias)
        return 0
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_remove_model(args: argparse.Namespace) -> int:
    """删除模型命令"""
    manager = ProviderManager()
    try:
        manager.remove_model(args.provider, args.name)
        return 0
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_list_models(args: argparse.Namespace) -> int:
    """列出提供商下的模型"""
    manager = ProviderManager()
    try:
        models = manager.list_models(args.provider)

        if not models:
            print(f"提供商 '{args.provider}' 暂无模型，请使用 'add-model' 命令添加")
            return 0

        print(f"提供商 '{args.provider}' 共有 {len(models)} 个模型:\n")
        for m in models:
            alias = f" (别名: {m['alias']})" if m.get('alias') != m['name'] else ""
            print(f"  • {m['name']}{alias}")
        return 0
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_set_config(args: argparse.Namespace) -> int:
    """设置提供商配置"""
    manager = ProviderManager()
    try:
        manager.set_provider_config(args.provider, args.api_url, args.api_key)
        return 0
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_get_config(args: argparse.Namespace) -> int:
    """获取提供商配置"""
    manager = ProviderManager()
    try:
        config = manager.get_provider_config(args.provider)
        print(f"提供商 '{args.provider}' 配置:")
        print(f"  API URL: {config.get('api_url') or '(未设置)'}")
        print(f"  API Key: {'***' + config.get('api_key', '')[-4:] if config.get('api_key') else '(未设置)'}")
        return 0
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def cmd_init_provider(args: argparse.Namespace) -> int:
    """初始化提供商（添加并设置配置）"""
    manager = ProviderManager()
    try:
        manager.add_provider(args.name, args.api_url, args.api_key)

        # 如果提供了模型，添加模型
        if args.models:
            for model_spec in args.models:
                # 格式: model_name 或 model_name:alias
                if ':' in model_spec:
                    model_name, alias = model_spec.split(':', 1)
                else:
                    model_name, alias = model_spec, ""
                manager.add_model(args.name, model_name, alias)

        return 0
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    """构建命令行解析器"""
    parser = argparse.ArgumentParser(
        description="AI Coding 配置切换器 - 管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 添加提供商
  ai-config-cli.py add-provider minimax --api-url https://api.minimaxi.com/anthropic --api-key sk-xxx

  # 添加模型
  ai-config-cli.py add-model minimax MiniMax-M2.5-highspeed --alias M2.5极速版

  # 初始化完整提供商配置
  ai-config-cli.py init minimax \\
    --api-url https://api.minimaxi.com/anthropic \\
    --api-key sk-xxx \\
    --model MiniMax-M2.5-highspeed:M2.5极速版 \\
    --model MiniMax-M2.7:M2.7标准版

  # 列出所有提供商
  ai-config-cli.py list

  # 列出提供商下的模型
  ai-config-cli.py list-models minimax

  # 设置提供商配置
  ai-config-cli.py set-config minimax --api-key sk-new-key

  # 删除模型
  ai-config-cli.py remove-model minimax MiniMax-M2.1

  # 删除提供商
  ai-config-cli.py remove-provider minimax
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # init: 初始化提供商（一步到位）
    init_parser = subparsers.add_parser("init", help="初始化提供商（添加提供商并设置配置）")
    init_parser.add_argument("name", help="提供商名称")
    init_parser.add_argument("--api-url", "-u", default="", help="API Base URL")
    init_parser.add_argument("--api-key", "-k", default="", help="API Key")
    init_parser.add_argument("--model", "-m", action="append", dest="models",
                            help="模型 (格式: model_name 或 model_name:alias，可多次使用)")
    init_parser.set_defaults(func=cmd_init_provider)

    # add-provider
    add_provider_parser = subparsers.add_parser("add-provider", help="添加提供商")
    add_provider_parser.add_argument("name", help="提供商名称")
    add_provider_parser.add_argument("--api-url", "-u", default="", help="API Base URL")
    add_provider_parser.add_argument("--api-key", "-k", default="", help="API Key")
    add_provider_parser.set_defaults(func=cmd_add_provider)

    # remove-provider
    remove_provider_parser = subparsers.add_parser("remove-provider", help="删除提供商")
    remove_provider_parser.add_argument("name", help="提供商名称")
    remove_provider_parser.set_defaults(func=cmd_remove_provider)

    # list (列出所有提供商)
    list_parser = subparsers.add_parser("list", help="列出所有提供商")
    list_parser.set_defaults(func=cmd_list_providers)

    # add-model
    add_model_parser = subparsers.add_parser("add-model", help="添加模型")
    add_model_parser.add_argument("provider", help="提供商名称")
    add_model_parser.add_argument("name", help="模型名称")
    add_model_parser.add_argument("--alias", "-a", default="", help="模型别名")
    add_model_parser.set_defaults(func=cmd_add_model)

    # remove-model
    remove_model_parser = subparsers.add_parser("remove-model", help="删除模型")
    remove_model_parser.add_argument("provider", help="提供商名称")
    remove_model_parser.add_argument("name", help="模型名称")
    remove_model_parser.set_defaults(func=cmd_remove_model)

    # list-models
    list_models_parser = subparsers.add_parser("list-models", help="列出提供商下的模型")
    list_models_parser.add_argument("provider", help="提供商名称")
    list_models_parser.set_defaults(func=cmd_list_models)

    # set-config
    set_config_parser = subparsers.add_parser("set-config", help="设置提供商配置")
    set_config_parser.add_argument("provider", help="提供商名称")
    set_config_parser.add_argument("--api-url", "-u", default=None, help="API Base URL")
    set_config_parser.add_argument("--api-key", "-k", default=None, help="API Key")
    set_config_parser.set_defaults(func=cmd_set_config)

    # get-config
    get_config_parser = subparsers.add_parser("get-config", help="查看提供商配置")
    get_config_parser.add_argument("provider", help="提供商名称")
    get_config_parser.set_defaults(func=cmd_get_config)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
