#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
    }
}


def list_candidate_files(config_dir: Path) -> list[Path]:
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
    }
    return mapping.get(text)


def open_folder_in_finder(folder_path: Path) -> None:
    """在访达中打开指定文件夹"""
    try:
        subprocess.run(["open", str(folder_path)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"警告: 无法打开文件夹: {e}", file=sys.stderr)


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


def switch_config(selected_file: Path, target_file: Path, backup_file: Path, dry_run: bool) -> None:
    selected_data = selected_file.read_bytes()

    if dry_run:
        print("\n[Dry Run] 将执行以下操作:")
        if target_file.exists():
            print(f"  1) 备份: {target_file} -> {backup_file}")
        else:
            print(f"  1) 跳过备份: 目标文件不存在 {target_file}")
        print(f"  2) 替换: {selected_file} -> {target_file}")
        return

    target_file.parent.mkdir(parents=True, exist_ok=True)
    backup_file.parent.mkdir(parents=True, exist_ok=True)

    if target_file.exists():
        shutil.copy2(target_file, backup_file)
        print(f"已备份当前配置到: {backup_file}")
    else:
        print(f"目标文件不存在，跳过备份: {target_file}")

    target_file.write_bytes(selected_data)
    print(f"已载入配置: {selected_file} -> {target_file}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI Coding 配置切换器（当前支持 Claude Code）"
    )
    parser.add_argument(
        "-t",
        "--tool",
        help="工具名称，例如: claude code / claude / claude_code",
    )
    parser.add_argument(
        "-c",
        "--config",
        help="配置文件名（相对于工具配置目录），例如: settings_580ai.json 或 settings.json.bak",
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

        selected_file = resolve_config_file(args.config, config_dir)

        switch_config(
            selected_file=selected_file,
            target_file=target_file,
            backup_file=backup_file,
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
