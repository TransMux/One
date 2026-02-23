#!/usr/bin/env python3
"""一键配置 CCB (Claude Code Bridge)"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

API_KEY_PLACEHOLDER = "YOUR_API_KEY_HERE"


def get_api_key():
    """获取用户输入的 API key"""
    while True:
        api_key = input("\n请输入你的 OpenAI API Key (sk-xxx): ").strip()
        if api_key and api_key.startswith("sk-"):
            return api_key
        print("[错误] 无效的 API key 格式，请重新输入")


def run_command(cmd, shell=True, check=True):
    """执行命令"""
    print(f"[执行] {cmd}")
    result = subprocess.run(cmd, shell=shell, check=check)
    return result.returncode == 0


def check_command_exists(cmd):
    """检查命令是否存在"""
    return run_command(f"which {cmd}", check=False)


def install_nvm_and_node():
    """安装 nvm 和 Node.js"""
    print("\n=== 安装 nvm 和 Node.js ===")

    nvm_dir = Path.home() / ".nvm"

    if nvm_dir.exists():
        print("[跳过] nvm 已安装")
    else:
        run_command(
            "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash"
        )

    nvm_sh = nvm_dir / "nvm.sh"
    if nvm_sh.exists():
        run_command(f'\. "{nvm_sh}" && nvm install 24 && nvm use 24')
    else:
        print("[错误] nvm.sh 不存在")
        return False

    if check_command_exists("node"):
        print("[跳过] Node.js 已安装")
    else:
        print("[提示] 请重启终端后继续")
        return False

    return True


def install_pnpm():
    """安装 pnpm"""
    print("\n=== 安装 pnpm ===")

    if check_command_exists("pnpm"):
        print("[跳过] pnpm 已安装")
        run_command("pnpm -v")
        return True

    run_command("corepack enable pnpm")
    return check_command_exists("pnpm")


def install_ai_tools():
    """安装所有 AI 工具"""
    print("\n=== 安装 AI 工具 ===")

    tools = [
        ("@google/gemini-cli", "gemini"),
        ("@anthropic-ai/claude-code", "claude"),
        ("opencode-ai@latest", "opencode"),
        ("@openai/codex", "codex"),
    ]

    for package, cmd_name in tools:
        if check_command_exists(cmd_name):
            print(f"[跳过] {cmd_name} 已安装")
        else:
            print(f"\n[安装] {package}")
            run_command(f"pnpm install -g {package}")


def copy_ai_configs(api_key):
    """复制 AI 配置文件"""
    print("\n=== 复制 AI 配置文件 ===")

    repo_dir = Path(__file__).parent
    config_dir = repo_dir / "config"
    home = Path.home()

    if not config_dir.exists():
        print(f"[提示] 配置目录不存在: {config_dir}")
        print("[提示] 请先运行 backup_configs.py 备份现有配置")
        return

    # 配置映射: 仓库源路径 -> 系统目标路径
    config_mappings = [
        # Claude Code
        (config_dir / ".claude" / "settings.json", home / ".claude" / "settings.json"),

        # Gemini CLI
        (config_dir / ".gemini" / ".env", home / ".gemini" / ".env"),
        (config_dir / ".gemini" / "settings.json", home / ".gemini" / "settings.json"),

        # Codex CLI
        (config_dir / ".codex" / "config.toml", home / ".codex" / "config.toml"),
        (config_dir / ".codex" / "auth.json", home / ".codex" / "auth.json"),
    ]

    for src, dst in config_mappings:
        if not src.exists():
            print(f"[跳过] 源文件不存在: {src.relative_to(repo_dir)}")
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)

        if dst.exists():
            print(f"[存在] {dst}")
        else:
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
                print(f"[复制] {src.relative_to(config_dir)} -> {dst}")
            else:
                # 复制并替换 API key 占位符
                content = src.read_text()
                msg = f"[复制] {src.relative_to(config_dir)} -> {dst}"
                if API_KEY_PLACEHOLDER in content:
                    content = content.replace(API_KEY_PLACEHOLDER, api_key)
                    msg += " (已替换 API key)"
                dst.write_text(content)
                print(msg)


def install_ccb():
    """安装 CCB"""
    print("\n=== 安装 CCB ===")

    ccb_dir = Path.home() / "projects" / "claude_code_bridge"

    if ccb_dir.exists():
        print(f"[跳过] CCB 已安装: {ccb_dir}")
        return True

    run_command(
        f"git clone https://github.com/bfly123/claude_code_bridge.git {ccb_dir}"
    )
    run_command(f"cd {ccb_dir} && ./install.sh install")

    return True


def main():
    print("=" * 50)
    print("CCB 一键配置脚本")
    print("=" * 50)

    # 获取 API key
    api_key = get_api_key()

    steps = [
        ("安装 nvm 和 Node.js", install_nvm_and_node),
        ("安装 pnpm", install_pnpm),
        ("安装 AI 工具", install_ai_tools),
        ("复制 AI 配置", lambda: copy_ai_configs(api_key)),
        ("安装 CCB", install_ccb),
    ]

    for name, func in steps:
        try:
            func()
        except Exception as e:
            print(f"[错误] {name} 失败: {e}")
            sys.exit(1)

    print("\n" + "=" * 50)
    print("[完成] CCB 配置完成!")
    print("=" * 50)


if __name__ == "__main__":
    main()
