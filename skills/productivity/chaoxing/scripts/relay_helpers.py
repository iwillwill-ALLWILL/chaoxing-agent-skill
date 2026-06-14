#!/usr/bin/env python3
"""Relay helper functions for 学习通 browser automation.

Supports both Chrome Relay (HTTP API) and OpenClaw browser tools.
Configure RELAY_MODE in your config or environment.
"""

import json
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────

RELAY_MODE = "chrome-relay"  # or "openclaw"
RELAY_PORT = 12123           # Edge: 12123, Chrome: 12122
RELAY_BASE = f"http://127.0.0.1:{RELAY_PORT}/call"
DEFAULT_TIMEOUT = 60


# ── Chrome Relay HTTP API ──────────────────────────────────────

def relay_call(tool: str, args: dict, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Call the Chrome Relay HTTP API."""
    data = json.dumps({"name": tool, "args": args}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(RELAY_BASE, data=data, headers={"content-type": "application/json"})
    try:
        raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"RELAY_HTTP_{e.code}: {body[:500]}")
    result = json.loads(raw)
    if not result.get("ok"):
        raise RuntimeError(json.dumps(result, ensure_ascii=False)[:1000])
    return result["data"]


def js_eval(tab_id: int, code: str, timeout_ms: int = 15000, timeout: int = 40) -> str:
    """Execute JavaScript in a browser tab and return the result."""
    return relay_call("chrome_evaluate", {
        "tabId": tab_id,
        "code": code,
        "timeoutMs": timeout_ms
    }, timeout).get("result")


def open_tab(url: str, timeout: int = 90) -> int:
    """Open a new tab and return its tabId."""
    return relay_call("chrome_navigate", {"url": url, "newTab": True}, timeout)["tabId"]


def close_tab(tab_id: int, timeout: int = 20):
    """Close a browser tab."""
    # Suppress onbeforeunload
    try:
        js_eval(tab_id, "window.onbeforeunload=null; window.onunload=null; return 'ok'", timeout_ms=5000, timeout=10)
    except Exception:
        pass
    try:
        relay_call("chrome_close_tabs", {"tabIds": [int(tab_id)]}, timeout)
    except Exception as e:
        print(f"  close warn {tab_id} {repr(e)[:120]}")


def wait_page(tab_id: int, max_wait: int = 45) -> dict:
    """Wait for a page to finish loading and return {url, title, text}."""
    for _ in range(max_wait):
        try:
            r = json.loads(js_eval(tab_id, """
                return JSON.stringify({
                    ready: document.readyState,
                    url: location.href,
                    title: document.title,
                    text: (document.body && document.body.innerText || '').slice(0, 1600)
                });
            """, timeout_ms=5000, timeout=12))
            if r.get("ready") == "complete" and len(r.get("text", "")) > 20:
                return r
        except Exception:
            pass
        time.sleep(1)
    return {"error": "timeout"}


def open_and_wait(url: str, max_wait: int = 45) -> tuple:
    """Open a new tab and wait for it to fully load."""
    tab_id = open_tab(url)
    page = wait_page(tab_id, max_wait)
    return tab_id, page


# ── OpenClaw-compatible wrappers ───────────────────────────────

# When using OpenClaw, these functions are replaced by built-in tools.
# This module provides a unified interface that works with either backend.

def navigate(url: str) -> dict:
    """Navigate to a URL. Returns tab/page info."""
    if RELAY_MODE == "openclaw":
        # In OpenClaw, the browser_navigate tool handles this
        raise NotImplementedError("Use browser_navigate in OpenClaw")
    tab_id, page = open_and_wait(url)
    return {"tabId": tab_id, "url": page.get("url"), "title": page.get("title")}


def evaluate(code: str, tab_id: int = None) -> str:
    """Execute JS and return result."""
    if RELAY_MODE == "openclaw":
        raise NotImplementedError("Use browser_console --expression in OpenClaw")
    return js_eval(tab_id, code)


def read_page(tab_id: int) -> str:
    """Read page content."""
    return evaluate("return (document.body && document.body.innerText || '');", tab_id)


# ── Utilities ──────────────────────────────────────────────────

def extract_json_from_js(js_result: str):
    """Parse JSON from a JS evaluation result that may have extra wrapper text."""
    # Some relay versions wrap the result in extra text
    try:
        return json.loads(js_result)
    except json.JSONDecodeError:
        # Try to find JSON inside the string
        start = js_result.find("{")
        if start >= 0:
            end = js_result.rfind("}") + 1
            return json.loads(js_result[start:end])
        start = js_result.find("[")
        if start >= 0:
            end = js_result.rfind("]") + 1
            return json.loads(js_result[start:end])
        raise


def clean_html_text(html: str) -> str:
    """Strip scripts and tags, return clean text."""
    import re
    clean = re.sub(r"<script[\s\S]*?</script>", "", html)
    clean = re.sub(r"<[^>]+>", " ", clean)
    return re.sub(r"\s+", " ", clean).strip()
