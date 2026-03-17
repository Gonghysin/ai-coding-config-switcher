#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent

TOOL_DEFS = {
    "claude code": {
        "config_dir": PROJECT_ROOT / "configs" / "claude_code",
        "target_file": Path("/Users/mac/.claude/settings.json"),
        "backup_file": PROJECT_ROOT / "configs" / "claude_code" / "settings.json.bak",
        "global_config": PROJECT_ROOT / "configs" / "claude_code" / "global_settings.json",
    },
    "opencode": {
        "config_dir": PROJECT_ROOT / "configs" / "opencode",
        "target_file": Path.home() / ".config" / "opencode" / "opencode.json",
        "backup_file": PROJECT_ROOT / "configs" / "opencode" / "opencode.json.bak",
        "global_config": PROJECT_ROOT / "configs" / "opencode" / "global_settings.json",
    }
}


def list_candidate_files(config_dir: Path) -> list[Path]:
    if not config_dir.exists():
        return []
    files = []
    for p in config_dir.iterdir():
        if not p.is_file():
            continue
        # 排除全局配置文件
        if p.name == "global_settings.json":
            continue
        if p.suffix.lower() in {".json", ".bak"}:
            files.append(p)
    return sorted(files, key=lambda p: p.name.lower())


def pick_from_menu(options: list[str], title: str, allow_open_folder: bool = False, folder_path: Path | None = None) -> str:
    if not options:
        raise ValueError("没有可选项")
    print(f"\n{title}")

    # 添加打开文件夹选项
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

        # 处理打开文件夹选项
        if choice == 0 and allow_open_folder and folder_path:
            open_folder_in_finder(folder_path)
            print(f"\n已在访达中打开: {folder_path}")
            print("请选择配置文件:")
            continue

        if 1 <= choice <= len(options):
            return options[choice - 1]
        print("编号超出范围，请重新输入。")


def normalize_tool_name(user_input: str) -> str | None:
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
    """在访达中打开指定文件夹"""
    try:
        subprocess.run(["open", str(folder_path)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"警告: 无法打开文件夹: {e}", file=sys.stderr)


def deep_merge_dict(base: dict, override: dict) -> dict:
    """
    深度合并两个字典，override 中的值会覆盖 base 中的值
    对于列表类型，会进行合并去重
    """
    result = base.copy()

    for key, value in override.items():
        if key in result:
            base_value = result[key]
            # 如果两者都是字典，递归合并
            if isinstance(base_value, dict) and isinstance(value, dict):
                result[key] = deep_merge_dict(base_value, value)
            # 如果两者都是列表，合并并去重
            elif isinstance(base_value, list) and isinstance(value, list):
                # 保持顺序，先 base 后 override，去重
                seen = set()
                merged = []
                for item in base_value + value:
                    if item not in seen:
                        seen.add(item)
                        merged.append(item)
                result[key] = merged
            else:
                # 其他情况直接覆盖
                result[key] = value
        else:
            result[key] = value

    return result


def load_and_merge_config(selected_file: Path, global_config_file: Path) -> dict:
    """
    加载选定的配置文件，并与全局配置合并
    全局配置优先级更高，会覆盖单个配置中的相同字段
    """
    # 加载选定的配置
    selected_config = json.loads(selected_file.read_text(encoding="utf-8"))

    # 如果全局配置文件不存在，直接返回选定的配置
    if not global_config_file.exists():
        print(f"提示: 全局配置文件不存在: {global_config_file}")
        return selected_config

    # 加载全局配置
    try:
        global_config = json.loads(global_config_file.read_text(encoding="utf-8"))
        print(f"已加载全局配置: {global_config_file}")
    except Exception as e:
        print(f"警告: 无法加载全局配置文件: {e}", file=sys.stderr)
        return selected_config

    # 合并配置：先应用选定配置，再应用全局配置（全局配置优先级更高）
    merged_config = deep_merge_dict(selected_config, global_config)

    return merged_config


def resolve_tool_name(tool_arg: str | None) -> str:
    available = sorted(TOOL_DEFS.keys())
    if tool_arg:
        normalized = normalize_tool_name(tool_arg)
        if not normalized or normalized not in TOOL_DEFS:
            names = ", ".join(available)
            raise ValueError(f"不支持的工具: {tool_arg}。当前支持: {names}")
        return normalized
    return pick_from_menu(available, "请选择要配置的 AI Coding 工具:")


def resolve_config_file(config_arg: str | None, config_dir: Path) -> Path:
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
    chosen_name = pick_from_menu(
        names,
        f"请选择要载入的配置文件（目录: {config_dir}）:",
        allow_open_folder=True,
        folder_path=config_dir
    )
    return config_dir / chosen_name


def switch_config(selected_file: Path, target_file: Path, backup_file: Path, global_config_file: Path, dry_run: bool) -> None:
    # 加载并合并配置
    merged_config = load_and_merge_config(selected_file, global_config_file)
    merged_data = json.dumps(merged_config, indent=2, ensure_ascii=False).encode("utf-8")

    if dry_run:
        print("\n[Dry Run] 将执行以下操作:")
        if target_file.exists():
            print(f"  1) 备份: {target_file} -> {backup_file}")
        else:
            print(f"  1) 跳过备份: 目标文件不存在 {target_file}")
        print(f"  2) 合并配置: {selected_file} + {global_config_file}")
        print(f"  3) 替换: 合并后的配置 -> {target_file}")
        print("\n合并后的配置预览:")
        print(json.dumps(merged_config, indent=2, ensure_ascii=False))
        return

    target_file.parent.mkdir(parents=True, exist_ok=True)
    backup_file.parent.mkdir(parents=True, exist_ok=True)

    if target_file.exists():
        shutil.copy2(target_file, backup_file)
        print(f"已备份当前配置到: {backup_file}")
    else:
        print(f"目标文件不存在，跳过备份: {target_file}")

    target_file.write_bytes(merged_data)
    print(f"已载入配置: {selected_file} + 全局配置 -> {target_file}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI Coding 配置切换器（支持 Claude Code、OpenCode）"
    )
    parser.add_argument(
        "-t",
        "--tool",
        help="工具名称，例如: claude code / opencode",
    )
    parser.add_argument(
        "-c",
        "--config",
        help="配置文件名（相对于工具配置目录），例如: settings_580ai.json 或 opencode_custom.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只展示操作，不写入文件",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        tool_name = resolve_tool_name(args.tool)
        tool_conf = TOOL_DEFS[tool_name]
        config_dir = tool_conf["config_dir"]
        target_file = tool_conf["target_file"]
        backup_file = tool_conf["backup_file"]
        global_config_file = tool_conf["global_config"]

        selected_file = resolve_config_file(args.config, config_dir)

        switch_config(
            selected_file=selected_file,
            target_file=target_file,
            backup_file=backup_file,
            global_config_file=global_config_file,
            dry_run=args.dry_run,
        )
        return 0
    except KeyboardInterrupt:
        print("\n已取消。")
        return 130
    except Exception as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
