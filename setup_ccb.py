#!/usr/bin/env python3
"""一键配置 CCB (Claude Code Bridge)"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

API_KEY_PLACEHOLDER = "YOUR_API_KEY_HERE"
CACHE_FILE = Path.home() / ".ccb_cache" / "api_key.txt"


def get_api_key():
    """获取用户输入的 API key，优先从缓存读取"""
    # 尝试从缓存读取
    if CACHE_FILE.exists():
        cached_key = CACHE_FILE.read_text().strip()
        if cached_key and cached_key.startswith("sk-"):
            print(f"[缓存] 使用已保存的 API key")
            return cached_key

    # 缓存不存在，要求用户输入
    while True:
        api_key = input("\n请输入你的 OpenAI API Key (sk-xxx): ").strip()
        if api_key and api_key.startswith("sk-"):
            # 保存到缓存
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(api_key)
            print(f"[保存] API key 已保存到 {CACHE_FILE}")
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
    print("\n=== 检查 Node.js ===")

    if check_command_exists("node"):
        run_command("node -v")
        print("[跳过] Node.js 已存在，跳过 nvm 和 pnpm 安装")
        return False

    print("[安装] Node.js 不存在，开始安装 nvm 和 Node.js")
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

    if check_command_exists("node"):
        print("[跳过] 使用系统 Node.js，跳过 pnpm")
        return False

    if check_command_exists("pnpm"):
        print("[跳过] pnpm 已安装")
        run_command("pnpm -v")
    else:
        run_command("corepack enable pnpm")

    # 运行 pnpm setup
    print("\n=== 运行 pnpm setup ===")
    run_command("pnpm setup")
    return True


def install_ai_tools():
    """安装所有 AI 工具"""
    print("\n=== 安装 AI 工具 ===")

    registry = "--registry=https://registry.npmmirror.com"
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
            run_command(f"npm i -g {package} {registry}")


def copy_ai_configs(api_key):
    """复制 AI 配置文件"""
    print("\n=== 复制 AI 配置文件 ===")

    repo_dir = Path(__file__).parent
    config_dir = repo_dir / "config"
    home = Path.home()

    # 创建/更新 ~/.claude.json 跳过 onboarding
    claude_json = home / ".claude.json"
    if claude_json.exists():
        import json
        data = json.loads(claude_json.read_text())
        data["hasCompletedOnboarding"] = True
        claude_json.write_text(json.dumps(data, indent=2))
        print(f"[更新] {claude_json}")
    else:
        claude_json.write_text('{\n  "hasCompletedOnboarding": true\n}\n')
        print(f"[创建] {claude_json}")

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

        # 删除已存在的文件/目录
        if dst.exists():
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()

        # 复制文件
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
    else:
        run_command(
            f"git clone https://github.com/bfly123/claude_code_bridge.git {ccb_dir}"
        )
        run_command(f"cd {ccb_dir} && ./install.sh install")

    # 添加 ccb 别名到 bashrc
    bashrc = Path.home() / ".bashrc"
    zshrc = Path.home() / ".zshrc"
    function_content = '''# CCB - 在 tmux 中运行 ccb
c() {
    if [ -z "$TMUX" ]; then
        tmux new-session -A -s ccb "ccb -a"
    else
        ccb -a
    fi
}
'''

    for rc_file in [bashrc, zshrc]:
        if rc_file.exists():
            content = rc_file.read_text()
            if "# CCB - 在 tmux 中运行 ccb" not in content:
                with open(rc_file, "a") as f:
                    f.write(f"\n{function_content}")
                print(f"[添加] 函数到 {rc_file.name}")

    return True


def install_tmux():
    """安装 tmux"""
    print("\n=== 安装 tmux ===")

    if check_command_exists("tmux"):
        print("[跳过] tmux 已安装")
    else:
        # macOS
        if run_command("which brew", check=False):
            run_command("brew install tmux")
        # Linux
        else:
            run_command("sudo apt-get install -y tmux || sudo yum install -y tmux")

    # 修复 ~/.bash_aliases 中的 cd 问题
    bash_aliases = Path.home() / ".bash_aliases"
    if bash_aliases.exists():
        content = bash_aliases.read_text()
        old_line = '[[ "$TERM_PROGRAM" != "vscode" ]] && cd "$ARNOLD_CMD_DIR"'
        new_line = '[[ "$TERM_PROGRAM" != "vscode" && -z "$TMUX" ]] && cd "$ARNOLD_CMD_DIR"'

        if old_line in content:
            content = content.replace(old_line, new_line)
            bash_aliases.write_text(content)
            print(f"[修复] {bash_aliases} - 跳过 tmux 会话的自动 cd")

    return True


def ask_open_tmux():
    """询问是否打开 tmux"""
    while True:
        answer = input("\n是否在当前目录打开 tmux? (y/n): ").strip().lower()
        if answer in ["y", "yes"]:
            run_command("tmux")
            break
        elif answer in ["n", "no"]:
            break
        print("[提示] 请输入 y 或 n")


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
        ("安装 tmux", install_tmux),
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
    print("\n[提示] 请运行 'source ~/.bashrc' 或 'source ~/.zshrc' 使别名生效")
    print("[提示] 使用 'c' 命令代替 'ccb -a'")

    # 询问是否打开 tmux
    ask_open_tmux()

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
