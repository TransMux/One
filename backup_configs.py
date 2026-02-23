#!/usr/bin/env python3
"""备份所有 AI 配置到仓库"""

import os
import re
import shutil
from pathlib import Path

API_KEY_PLACEHOLDER = "YOUR_API_KEY_HERE"
API_KEY_PATTERN = r"sk-[a-zA-Z0-9]{32}"


def sanitize_api_keys(content):
    """替换 API key 为占位符"""
    return re.sub(API_KEY_PATTERN, API_KEY_PLACEHOLDER, content)


def backup_configs():
    """备份配置文件到仓库"""
    print("=" * 50)
    print("备份 AI 配置文件")
    print("=" * 50)

    repo_dir = Path(__file__).parent
    home = Path.home()

    # 配置映射: 源路径 -> 仓库目标路径
    config_mappings = [
        # Claude Code
        (home / ".claude" / "settings.json", repo_dir / "config" / ".claude" / "settings.json"),

        # Gemini CLI
        (home / ".gemini" / ".env", repo_dir / "config" / ".gemini" / ".env"),
        (home / ".gemini" / "settings.json", repo_dir / "config" / ".gemini" / "settings.json"),

        # Codex CLI
        (home / ".codex" / "config.toml", repo_dir / "config" / ".codex" / "config.toml"),
        (home / ".codex" / "auth.json", repo_dir / "config" / ".codex" / "auth.json"),
    ]

    for src, dst in config_mappings:
        if not src.exists():
            print(f"[跳过] 源不存在: {src}")
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)

        if dst.exists():
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()

        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
            print(f"[备份] {src.name} -> ")
        else:
            # 复制并清理 API key
            content = src.read_text()
            sanitized = sanitize_api_keys(content)
            dst.write_text(sanitized)
            msg = f"[备份] {src.name} -> {dst.relative_to(repo_dir)}"
            if content != sanitized:
                msg += " (已清理 API key)"
            print(msg)

    print("\n" + "=" * 50)
    print("[完成] 配置备份完成!")
    print(f"[位置] {repo_dir / 'config'}")
    print("=" * 50)


if __name__ == "__main__":
    backup_configs()
