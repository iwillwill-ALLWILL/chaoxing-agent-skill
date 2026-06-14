#!/usr/bin/env python3
"""
超星滑块 CAPTCHA 自动解决 — 后端流水线

通过 Capsolver VisionEngine 计算滑块距离，调用 超星验证API，
获取 validate token 并注入浏览器页面，实现零键鼠全自动绕过。

用法:
    python captcha_pipeline.py <tab_id>

前置:
    - 浏览器 Relay 已运行（Chrome Relay 端口 12123）
    - Capsolver 账号已配置（设置 CAPSOLVER_KEY 环境变量）
    - 浏览器标签页在 examnotes 页面
"""

import json
import sys
import time
import hashlib
import random
import uuid as uuid_lib
import base64
import subprocess
import os
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from relay_helpers import js_eval

# ── Configuration ──────────────────────────────────────────────

CAPSOLVER_KEY = os.environ.get("CAPSOLVER_KEY", "CAP-YOUR_KEY_HERE")
CAPTCHA_API = "https://captcha.chaoxing.com"
CAPSOLVER_API = "https://api.capsolver.com/createTask"


def md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def gen_uuid() -> str:
    return str(uuid_lib.uuid4())


def random_digit(n: int = 6) -> int:
    return random.randint(10 ** (n - 1), 10**n - 1)


def now_ms() -> int:
    return int(time.time() * 1000)


def curl_get(url: str, timeout: int = 15) -> str:
    """Use curl -k for systems with transparent proxy."""
    result = subprocess.run(
        ["curl", "-k", "-s", "--max-time", str(timeout), url],
        capture_output=True, text=True, timeout=timeout + 5,
    )
    return result.stdout


def jsonp_parse(text: str) -> dict:
    """Parse JSONP callback response."""
    match = re.search(r"\(([\s\S]*)\)", text)
    if match:
        return json.loads(match.group(1))
    return json.loads(text)


def download_raw(url: str) -> bytes:
    """Download image as raw bytes."""
    result = subprocess.run(
        ["curl", "-k", "-s", "--max-time", "15",
         "-H", "User-Agent: Mozilla/5.0",
         "-H", "Referer: https://mooc1.chaoxing.com/",
         url],
        capture_output=True, timeout=20,
    )
    result.check_returncode()
    return result.stdout


def capsolver_distance(puzzle_b64: str, bg_b64: str) -> int:
    """Call Capsolver VisionEngine slider_1 and return gap distance."""
    payload = {
        "clientKey": CAPSOLVER_KEY,
        "task": {
            "type": "VisionEngine",
            "module": "slider_1",
            "image": puzzle_b64,
            "imageBackground": bg_b64,
            "websiteURL": "https://mooc1.chaoxing.com",
        },
    }

    # Write to temp file to avoid Windows command-line length limit
    tmp_path = Path("capsolver_payload_tmp.json")
    tmp_path.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        ["curl", "-k", "-s", "-X", "POST", CAPSOLVER_API,
         "-H", "Content-Type: application/json",
         "-d", f"@{tmp_path}"],
        capture_output=True, text=True, timeout=30,
    )
    tmp_path.unlink(missing_ok=True)

    data = json.loads(result.stdout)
    if data.get("errorId") != 0 or data.get("status") != "ready":
        raise RuntimeError(f"Capsolver error: {data}")

    return data["solution"]["distance"]


def solve_captcha(captcha_id: str) -> str:
    """Full CAPTCHA pipeline: conf → image → Capsolver → verify → validate token."""
    ts = now_ms()

    # Step 1: Get server time
    conf_url = (
        f"{CAPTCHA_API}/captcha/get/conf"
        f"?callback=cx_captcha_function&captchaId={captcha_id}&_={ts}"
    )
    conf = jsonp_parse(curl_get(conf_url))
    server_time = conf["t"]
    print(f"  Server time: {server_time}")

    # Step 2: Get image token + URLs
    rn = random_digit()
    ck = md5(f"{server_time}{rn}")
    tok = f"{md5(f'{server_time}{captcha_id}slide{ck}')}:{server_time + 300000}"
    iv = gen_uuid()

    img_url = (
        f"{CAPTCHA_API}/captcha/get/verification/image"
        f"?callback=cx_captcha_function"
        f"&captchaId={captcha_id}"
        f"&type=slide"
        f"&version=1.1.20"
        f"&captchaKey={ck}"
        f"&token={tok}"
        f"&referer=https://mooc1.chaoxing.com"
        f"&iv={iv}"
        f"&_={ts}"
    )
    img_data = jsonp_parse(curl_get(img_url))
    image_token = img_data["token"]
    bg_url = img_data["imageVerificationVo"]["shadeImage"]
    sm_url = img_data["imageVerificationVo"]["cutoutImage"]
    print(f"  Image token: {image_token[:20]}...")

    # Step 3: Download images (RAW format)
    bg_bytes = download_raw(bg_url)
    sm_bytes = download_raw(sm_url)
    bg_b64 = base64.b64encode(bg_bytes).decode()
    sm_b64 = base64.b64encode(sm_bytes).decode()
    print(f"  Images: bg={len(bg_bytes)}B, puzzle={len(sm_bytes)}B")

    # Step 4: Capsolver
    distance = capsolver_distance(sm_b64, bg_b64)
    print(f"  Capsolver distance: {distance}")

    # Step 5: Verify with 超星 API
    click_arr = json.dumps([{"x": distance}])
    verify_url = (
        f"{CAPTCHA_API}/captcha/check/verification/result"
        f"?callback=cx_captcha_function"
        f"&captchaId={captcha_id}"
        f"&type=slide"
        f"&token={image_token}"
        f"&textClickArr={click_arr}"
        f"&coordinate=[]"
        f"&runEnv=10"
        f"&version=1.1.20"
        f"&t=a"
        f"&iv={gen_uuid()}"
        f"&_={now_ms()}"
    )
    verify = jsonp_parse(curl_get(verify_url))
    if not verify.get("result"):
        raise RuntimeError(f"Verify failed: {verify}")

    extra = json.loads(verify.get("extraData", "{}"))
    validate_token = extra.get("validate", "")
    print(f"  Validate token: {validate_token[:20]}...")
    return validate_token


def inject_into_page(tab_id: int, validate_token: str, is_retake: bool = True):
    """Inject validate token into examnotes page and trigger exam entry."""
    reset = "true" if is_retake else "false"
    code = f"""
    document.querySelector('#captchavalidate').value = '{validate_token}';
    document.querySelector('#captchaCheck').value = '0';
    document.querySelector('#examCheck').value = '0';
    var origShowCXCaptcha = showCXCaptcha;
    showCXCaptcha = function(cb) {{ if (typeof cb === 'function') cb(); }};
    jumpExam('{reset}');
    return 'injected';
    """
    result = js_eval(tab_id, code, timeout_ms=10000, timeout=20)
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python captcha_pipeline.py <tab_id>")
        print("  tab_id: Browser tab on examnotes page")
        sys.exit(1)

    if CAPSOLVER_KEY == "CAP-YOUR_KEY_HERE":
        print("ERROR: Set CAPSOLVER_KEY environment variable with your Capsolver API key")
        print("  $env:CAPSOLVER_KEY='CAP-...'  (PowerShell)")
        print("  export CAPSOLVER_KEY='CAP-...'  (bash)")
        sys.exit(1)

    tab_id = int(sys.argv[1])

    # Extract captchaId from page
    captcha_id = js_eval(
        tab_id,
        "return document.querySelector('#captchaCaptchaId')?.value || '';",
        timeout_ms=5000, timeout=10,
    )
    if not captcha_id:
        print("ERROR: Could not find captchaId on page. Is this an examnotes page?")
        sys.exit(1)

    print(f"Captcha ID: {captcha_id}")
    print("Starting CAPTCHA pipeline...")

    try:
        validate_token = solve_captcha(captcha_id)
        result = inject_into_page(tab_id, validate_token)
        print(f"Injection result: {result}")
        print("✓ CAPTCHA solved. Exam should be loading in the browser.")
    except Exception as e:
        print(f"✗ CAPTCHA pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
