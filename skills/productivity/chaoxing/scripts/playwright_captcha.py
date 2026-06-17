#!/usr/bin/env python3
"""
超星滑块 CAPTCHA 解决 — Playwright CLI 方案

为没有内置浏览器控制的 Agent（如 Claude Code、Open Code）提供
基于 Playwright CLI 的 CAPTCHA 解决方案。

支持两种模式：
1. 自动模式：使用 Capsolver API 自动解决
2. 手动模式：打开有头浏览器，用户手动完成滑块验证

用法:
    # 自动模式（需要 Capsolver API key）
    export CAPSOLVER_KEY="CAP-..."
    python playwright_captcha.py --auto

    # 手动模式（打开浏览器让用户操作）
    python playwright_captcha.py --manual

    # 指定考试页面 URL
    python playwright_captcha.py --manual --url "https://mooc1.chaoxing.com/exam-ans/..."

前置:
    - Playwright CLI 已安装 (npm install -g @playwright/cli)
    - 浏览器已安装 (playwright install chromium)
"""

import argparse
import json
import subprocess
import sys
import time
import os
from pathlib import Path


def run_playwright(cmd: str, timeout: int = 30) -> str:
    """执行 playwright-cli 命令并返回输出。"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return ""
    except Exception as e:
        print(f"Error running command: {e}")
        return ""


def get_page_snapshot() -> str:
    """获取当前页面快照。"""
    return run_playwright("playwright-cli snapshot")


def eval_js(code: str) -> str:
    """在页面中执行 JavaScript 代码。"""
    # 转义代码中的引号
    escaped_code = code.replace('"', '\\"').replace('\n', '\\n')
    cmd = f'playwright-cli eval "{escaped_code}"'
    return run_playwright(cmd)


def click_element(selector: str) -> bool:
    """点击页面元素。"""
    cmd = f'playwright-cli click {selector}'
    result = run_playwright(cmd)
    return "Error" not in result


def open_browser_headed(url: str) -> bool:
    """以有头模式打开浏览器。"""
    cmd = f'playwright-cli open --browser=chrome "{url}"'
    result = run_playwright(cmd, timeout=60)
    return "opened" in result.lower() or "Browser" in result


def open_browser_headless(url: str) -> bool:
    """以无头模式打开浏览器。"""
    cmd = f'playwright-cli open "{url}"'
    result = run_playwright(cmd, timeout=60)
    return "opened" in result.lower() or "Browser" in result


def close_browser():
    """关闭浏览器。"""
    run_playwright("playwright-cli close")


def manual_captcha_solve(url: str):
    """
    手动模式：打开有头浏览器，让用户手动完成滑块验证。
    
    流程：
    1. 以有头模式打开浏览器
    2. 导航到考试页面
    3. 等待用户完成验证
    4. 检测验证是否成功
    """
    print("=" * 60)
    print("手动模式 - 浏览器滑块验证")
    print("=" * 60)
    print()
    print("即将打开浏览器，请完成以下操作：")
    print("1. 登录学习通（如果需要）")
    print("2. 完成滑块验证")
    print("3. 进入考试页面")
    print("4. 完成后按回车键继续...")
    print()
    
    # 以有头模式打开浏览器
    print("正在打开浏览器...")
    if not open_browser_headed(url):
        print("错误：无法打开浏览器")
        print("请确保已安装 Playwright CLI：npm install -g @playwright/cli")
        print("并安装浏览器：playwright install chromium")
        return False
    
    print("浏览器已打开，请完成验证...")
    print()
    
    # 等待用户完成验证
    input("完成验证后按回车键继续...")
    
    # 检查是否成功进入考试页面
    print("检查验证状态...")
    snapshot = get_page_snapshot()
    
    if "captcha" in snapshot.lower() or "验证" in snapshot:
        print("警告：似乎仍在验证页面")
        print("请确保已完成验证，然后重试")
        return False
    
    print("✓ 验证完成！")
    return True


def auto_captcha_solve(url: str, capsolver_key: str):
    """
    自动模式：使用 Capsolver API 自动解决 CAPTCHA。
    
    流程：
    1. 打开浏览器
    2. 获取 CAPTCHA 信息
    3. 调用 Capsolver API
    4. 注入验证结果
    """
    print("=" * 60)
    print("自动模式 - Capsolver API")
    print("=" * 60)
    print()
    
    if not capsolver_key:
        print("错误：需要设置 CAPSOLVER_KEY 环境变量")
        print("export CAPSOLVER_KEY='CAP-...'")
        return False
    
    # 打开浏览器
    print("正在打开浏览器...")
    if not open_browser_headless(url):
        print("错误：无法打开浏览器")
        return False
    
    print("浏览器已打开，正在获取 CAPTCHA 信息...")
    
    # 获取 CAPTCHA ID
    captcha_id_js = """
    (() => {
        var el = document.querySelector('#captchaCaptchaId');
        return el ? el.value : '';
    })()
    """
    captcha_id = eval_js(captcha_id_js)
    
    if not captcha_id:
        print("未找到 CAPTCHA，可能已经验证过")
        return True
    
    print(f"CAPTCHA ID: {captcha_id}")
    
    # 调用 captcha_pipeline.py
    print("正在调用 CAPTCHA 解决脚本...")
    
    # 获取当前标签页 ID（简化处理，使用标签 0）
    cmd = f"python {Path(__file__).parent}/captcha_pipeline.py 0"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✓ CAPTCHA 自动解决成功！")
        return True
    else:
        print(f"✗ CAPTCHA 自动解决失败: {result.stderr}")
        print("请尝试手动模式：python playwright_captcha.py --manual")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="超星滑块 CAPTCHA 解决 — Playwright CLI 方案",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 手动模式（推荐用于首次验证）
  python playwright_captcha.py --manual

  # 自动模式（需要 Capsolver API key）
  export CAPSOLVER_KEY="CAP-..."
  python playwright_captcha.py --auto

  # 指定考试页面 URL
  python playwright_captcha.py --manual --url "https://mooc1.chaoxing.com/exam-ans/..."
        """
    )
    
    parser.add_argument(
        "--manual",
        action="store_true",
        help="手动模式：打开有头浏览器，用户手动完成验证"
    )
    
    parser.add_argument(
        "--auto",
        action="store_true",
        help="自动模式：使用 Capsolver API 自动解决"
    )
    
    parser.add_argument(
        "--url",
        default="https://mooc1.chaoxing.com/exam-ans/exam/test/examcode/examnotes",
        help="考试页面 URL"
    )
    
    parser.add_argument(
        "--capsolver-key",
        default=os.environ.get("CAPSOLVER_KEY", ""),
        help="Capsolver API key（也可通过 CAPSOLVER_KEY 环境变量设置）"
    )
    
    args = parser.parse_args()
    
    # 默认使用手动模式
    if not args.manual and not args.auto:
        args.manual = True
    
    print("超星滑块 CAPTCHA 解决方案 - Playwright CLI")
    print()
    
    if args.manual:
        success = manual_captcha_solve(args.url)
    else:
        success = auto_captcha_solve(args.url, args.capsolver_key)
    
    if success:
        print()
        print("操作完成！")
    else:
        print()
        print("操作失败，请检查错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
