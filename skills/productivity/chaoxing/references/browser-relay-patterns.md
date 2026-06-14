# Browser Relay Integration Patterns

## Architecture

学习通's `uf` cookie is TLS-fingerprint-bound. Direct HTTP API calls (Python `urllib`, `curl` from terminal) always redirect to login. All interactions MUST go through the user's existing browser session.

## Relay Options

### Option A: Chrome Relay (Recommended for Hermes Agent)

Chrome Relay uses a native messaging host to connect a CLI to the user's existing Chrome/Edge browser via CDP.

**Start the relay server:**
```bash
# For Edge (port 12123):
node "$HOME/.chrome-relay/native-host-edge-12123.js" &

# For Chrome (port 12122):
node "$HOME/.chrome-relay/native-host-chrome-12122.js" &
```

Verify it's running:
```bash
curl -s http://127.0.0.1:12123/
# Should return 404 (not connection refused)
```

**Key commands:**
```bash
CLI="$HOME/.chrome-relay/cli-edge-12123.js"

# List open tabs
node "$CLI" tabs

# Navigate (opens new tab, returns tabId)
node "$CLI" navigate "https://mooc1.chaoxing.com/..."

# Execute JavaScript (return value works in newer versions)
node "$CLI" js --tab <tabId> "return document.title"

# Read page text
node "$CLI" read --tab <tabId>

# Click by selector
node "$CLI" click --tab <tabId> ".face_agreement"

# Screenshot
node "$CLI" screenshot --tab <tabId> -o /tmp/screenshot.png

# Close tab
node "$CLI" close <tabId>
```

### Option B: OpenClaw Browser Tools

OpenClaw provides `browser_navigate`, `browser_snapshot`, `browser_click`, `browser_console` (with expression for JS eval), and `browser_vision`.

**Equivalent mapping:**
| Chrome Relay | OpenClaw |
|---|---|
| `tabs` | `browser_navigate` initializes session |
| `navigate` | `browser_navigate` |
| `read` | `browser_snapshot` |
| `click` | `browser_click` |
| `js --tab <id> "..."` | `browser_console --expression "..."` |
| `screenshot` | `browser_vision` |

### Option C: Playwright CDP Connection

Connect to existing Edge via `DevToolsActivePort`:
```python
import asyncio
from playwright.async_api import async_playwright

async def connect():
    # Read port from %LOCALAPPDATA%\Microsoft\Edge\User Data\DevToolsActivePort
    ws_url = 'ws://127.0.0.1:<port>/devtools/browser/<uuid>'
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(ws_url)
        page = browser.contexts[0].pages[0]
        await page.goto('https://mooc1.chaoxing.com/...')
        title = await page.title()
```

## Common Patterns

### Pattern 1: Navigate and Wait for Page Load

```javascript
// After navigating, wait for page to be ready
function waitForPage(tab, timeoutMs) {
  var start = Date.now();
  while (Date.now() - start < timeoutMs) {
    var ready = /* execute JS: */ "return document.readyState";
    var textLen = /* execute JS: */ "return (document.body?.innerText || '').length";
    if (ready === 'complete' && textLen > 20) break;
    sleep(1000);
  }
}
```

### Pattern 2: Handle Leave-Confirmation Dialogs

学习通 pages may trigger `onbeforeunload` confirmations. Suppress them before navigating away:

```javascript
window.onbeforeunload = null;
window.onunload = null;
```

### Pattern 3: Open New Tabs for Side Navigation

When clicking links that may trigger leave-confirmation dialogs or lose state, open in new tabs:

```bash
# Instead of navigating the current tab, open a new one
node "$CLI" navigate --new-tab "https://mooc1.chaoxing.com/..."

# Clean up unused tabs after
node "$CLI" close <oldTabId>
```

### Pattern 4: Same-Origin Fetch for Batch Operations

From any `mooc1.chaoxing.com` page, same-origin `fetch()` works without CORS:

```javascript
// Batch-check multiple exam lists
async function batchCheck(urls) {
  var results = [];
  for (var url of urls) {
    var resp = await fetch(url, {credentials: 'include', redirect: 'follow'});
    var html = await resp.text();
    results.push({url: resp.url, length: html.length});
  }
  return results;
}
```

This is MUCH faster than navigating each URL in a browser tab (~1s per course vs ~10s per course).

## Relay Recovery

**Symptom**: `curl http://localhost:12123/` returns "Connection refused".

**Fix**:
```bash
# Kill any stale relay processes
pkill -f native-host-edge

# Restart
node "$HOME/.chrome-relay/native-host-edge-12123.js" &

# Verify
sleep 3
curl -s http://127.0.0.1:12123/
```

**If relay CLI shows "extension not connected":**
- Ensure Edge is running and the Chrome Relay extension is installed
- Check extension is enabled in `edge://extensions`
- The relay uses a native messaging host; re-run `chrome-relay install` if needed
