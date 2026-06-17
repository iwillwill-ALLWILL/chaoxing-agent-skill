# CAPTCHA Slider Auto-Solve — Full Pipeline

The exam-entry slider CAPTCHA (`captcha.chaoxing.com`) is the only user-interaction step. This document covers the complete automated pipeline that bypasses it with zero mouse/keyboard input.

## Architecture

```
Browser Page                    Backend Pipeline
─────────────                   ────────────────
showCXCaptcha()
  ↓
fetch conf → captchaId ─────→  Step 1: Get server time
fetch image → bg+sm URLs ───→  Step 2: Get image token + URLs
                                Step 3: Download images (preserve RAW format)
                                Step 4: Capsolver VisionEngine → distance
                                Step 5: CAPTCHA verify API → validate token
                                Step 6: Return validate ←
  ↓
Inject validate into page
  ↓
jumpExam('true') → enter exam
```

## Step-by-Step

### Step 1: Get CAPTCHA Config (Server Time)

```
GET https://captcha.chaoxing.com/captcha/get/conf
  ?callback=cx_captcha_function
  &captchaId={captchaId}
  &_={timestamp_ms}

Response: {"t": 1781099608826}
```

The `captchaId` is embedded in the examnotes page HTML. It's typically constant per exam entry page but changes per session.

### Step 2: Get Verification Image + Token

Generate authentication parameters:
- `captchaKey = md5(serverTime + random6digit)`
- `token = md5(serverTime + captchaId + "slide" + captchaKey) + ":" + (serverTime + 300000)`
- `iv = uuid4()`

```
GET https://captcha.chaoxing.com/captcha/get/verification/image
  ?callback=cx_captcha_function
  &captchaId={captchaId}
  &type=slide
  &version=1.1.20
  &captchaKey={captchaKey}
  &token={token}
  &referer=https://mooc1.chaoxing.com
  &iv={uuid}
  &_={timestamp_ms}

Response: {
  "token": "image_session_token",
  "imageVerificationVo": {
    "shadeImage": "https://captcha-b.chaoxing.com/slide/big/{hash}.jpg",
    "cutoutImage": "https://captcha-b.chaoxing.com/slide/small/{hash}.png"
  }
}
```

**Image format**:
- `shadeImage` = background with cutout gap (JPEG, 320×160)
- `cutoutImage` = puzzle piece with transparency (PNG, 56×160)

### Step 3: Download Images (PRESERVE RAW FORMAT)

**CRITICAL**: Do NOT convert image formats.
- PNG→JPEG conversion destroys puzzle piece transparency → Capsolver returns distance=6 instead of ~215
- JPEG→PNG conversion adds artifacts → distance drifts by 30-80px
- Always send RAW bytes as received from the server

Download via `curl -k` or browser `fetch()`:
```bash
curl -k -s -H "User-Agent: Mozilla/5.0" \
  -H "Referer: https://mooc1.chaoxing.com/" \
  "https://captcha-b.chaoxing.com/slide/big/{hash}.jpg" -o bg.jpg

curl -k -s -H "User-Agent: Mozilla/5.0" \
  -H "Referer: https://mooc1.chaoxing.com/" \
  "https://captcha-b.chaoxing.com/slide/small/{hash}.png" -o puzzle.png
```

Notes:
- Images are served from `captcha-b.chaoxing.com` without auth/cookies
- `curl -k` is needed on systems with transparent proxy (SSL interception)
- The `Referer` header is required

### Step 4: Capsolver VisionEngine

```json
POST https://api.capsolver.com/createTask
{
  "clientKey": "CAP-YOUR_KEY_HERE",
  "task": {
    "type": "VisionEngine",
    "module": "slider_1",
    "image": "<base64_puzzle_png>",
    "imageBackground": "<base64_background_jpg>",
    "websiteURL": "https://mooc1.chaoxing.com"
  }
}

Response: {
  "errorId": 0,
  "status": "ready",
  "solution": {"distance": 215}
}
```

**Key details**:
- Response is SYNCHRONOUS — no polling needed
- Cost: ~$0.001 per solve
- Image field order: `image`=puzzle piece, `imageBackground`=background (non-intuitive — puzzle goes first!)
- Distance represents pixels from left edge of background
- `websiteURL` helps Capsolver classify the CAPTCHA type

### Step 5: Verify with 超星 CAPTCHA API

```
GET https://captcha.chaoxing.com/captcha/check/verification/result
  ?callback=cx_captcha_function
  &captchaId={captchaId}
  &type=slide
  &token={imageToken}
  &textClickArr=[{"x":215}]
  &coordinate=[]
  &runEnv=10
  &version=1.1.20
  &t=a
  &iv={uuid}
  &_={timestamp_ms}

Response: {
  "result": true,
  "extraData": "{\"validate\":\"validate_abc123...\"}"
}
```

**Key details**:
- `textClickArr` = `[{"x": distance}]` — the gap distance from Capsolver
- `t=a` simulates `isTrusted=true` (real mouse event)
- `runEnv=10` — browser environment indicator
- The `validate` token in `extraData` is what gets injected into the page

### Step 6: Inject into Page via Browser Relay

```javascript
// Set the validate token
document.querySelector('#captchavalidate').value = validateToken;

// Disable CAPTCHA check
document.querySelector('#captchaCheck').value = '0';

// Hijack showCXCaptcha to skip the slider UI
var origShowCXCaptcha = showCXCaptcha;
showCXCaptcha = function(callback) {
    // Call the callback directly — skip the slider entirely
    if (typeof callback === 'function') callback();
};

// Trigger exam entry
jumpExam('true');  // 'true' = retake flow, uses reTestAction
```

## jumpExam Source (Reverse-Engineered)

```javascript
function jumpExam(reset, faceDetectionResult) {
    var callBack = function () {
        var toAnswerPage = function() {
            var url = document.querySelector('#startBtn').getAttribute('data');
            location.href = url;
        };
        if (reset == 'true') {
            reTestAction(function () { toAnswerPage(); });
        } else {
            toAnswerPage();
        }
    };
    var examCheck = document.querySelector('#examCheck').value;
    var captchaCheck = document.querySelector('#captchaCheck').value;
    var captchaCallBack = function() {
        if (examCheck == 1 || captchaCheck == 1) {
            preCheckAction(callBack);
        } else {
            callBack();
        }
    };
    if (captchaCheck == 1) {
        showCXCaptcha(captchaCallBack);
    } else {
        captchaCallBack();
    }
}
```

### jumpExam Flow Matrix

| examCheck | captchaCheck | Flow |
|-----------|-------------|------|
| 1 | 1 | showCXCaptcha → slider → captchaCallBack → preCheckAction → startExamSignature(native host) → checkAction(AJAX) → enc → callBack → navigate to exam |
| 1 | 0 | captchaCallBack → preCheckAction → ... (NEEDS valid captchavalidate in hidden input!) |
| 0 | 0 | captchaCallBack → callBack → reTestAction (if reset=true) → toAnswerPage → navigate |

**Bypass strategy**: 
- Set `examCheck=0, captchaCheck=0` → skip preCheckAction entirely
- For retakes: `reTestAction` handles enc → navigation works
- For first attempts: `toAnswerPage` navigates with `enc=?` → "无权限访问" (no permission)
- **Solution**: Get real validate token from Capsolver pipeline → inject into `#captchavalidate` → set `captchaCheck=0` → override `showCXCaptcha` → call `jumpExam('true')`

## Two Deployment Options

### Option A: Backend Pipeline (Python script)

Run from terminal; good for on-demand use:

```bash
python scripts/captcha_pipeline.py <tab_id>
```

Full implementation in `scripts/captcha_pipeline.py`.

### Option B: Tampermonkey Userscript (Auto-solve)

Install once, auto-solves every CAPTCHA on exam entry pages. Full implementation in `scripts/cx-captcha-auto.user.js`.

**Installation**:
1. Install Tampermonkey extension in Edge/Chrome
2. Drag `cx-captcha-auto.user.js` into browser window
3. Click "Install"
4. Navigate to any exam entry page — CAPTCHA auto-solves

## Alternative: OpenCV Gap Detection

When Capsolver is unavailable, OpenCV template matching can provide a fallback:

```python
import cv2
import numpy as np

# Download raw server images (see Step 3)
bg = cv2.imread('bg.jpg', cv2.IMREAD_GRAYSCALE)
sm = cv2.imread('puzzle.png', cv2.IMREAD_GRAYSCALE)

# Template matching
result = cv2.matchTemplate(bg, sm, cv2.TM_CCOEFF_NORMED)
_, max_val, _, max_loc = cv2.minMaxLoc(result)

gap = max_loc[0]  # x-coordinate of best match
# Confidence: max_val > 0.8 = reliable, 0.6-0.8 = usable, < 0.6 = unreliable
```

**Accuracy**: OpenCV distances are typically within ±10px of Capsolver. Use Capsolver when available for higher accuracy; OpenCV as fallback.

## Common Pitfalls

1. **Image format conversion**: PNG puzzle → JPEG breaks Capsolver matching. Distance returns as 6 (default/error value). Always use RAW bytes.

2. **Image field order**: `image`=puzzle piece, `imageBackground`=background. Swapping them gives `angle:0` (misidentified as rotate CAPTCHA).

3. **Token session binding**: The validate token is tied to the page's CAPTCHA session. Must use the token from the CURRENT page's image fetch.

4. **Verify API reliability**: `captcha.chaoxing.com/captcha/check/verification/result` occasionally returns empty responses. Retry with fresh conf (token expires at `serverTime + 300000` = 5 minutes).

5. **curl vs Python requests**: On some systems with transparent proxy, Python `requests` fails with SSL errors but `curl -k` works. For Capsolver POST with large base64 payloads, write JSON to temp file and use `curl -d @file.json` to avoid command-line length limits.

6. **BUTTON_IMAGE_WIDTH**: The CAPTCHA source (`load-t.min.js`) defines `BUTTON_IMAGE_WIDTH=40`. The server receives `parseInt(btn.css.left) - 40` as the gap. However, Capsolver's distance goes directly to verify API which handles this internally — no manual offset needed.

7. **Rate limiting**: Rapid verify API calls (>15 in quick succession) get rate-limited. If Capsolver distance is wrong, spread retry attempts with different distances.

8. **captchaId**: The `captchaId` is embedded in the examnotes page HTML. It may change per session but is typically constant for a given user. Extract from page: `document.querySelector('#captchaCaptchaId')?.value`.

## Verification

After inject + jumpExam('true'):
- [ ] Page navigates to exam URL (NOT "无权限访问")
- [ ] Exam questions are visible
- [ ] Timer is counting down
- [ ] `topreview()` works (loads all questions)

## Cost

- Capsolver VisionEngine slider_1: ~$0.001 per solve
- A typical exam session needs 1-2 CAPTCHA solves (entry + retake)
- **⚠️ Capsolver no longer offers free credits — minimum top-up is $6**
- $6 balance is sufficient for hundreds of exams
- **Free alternative**: Use `scripts/playwright_captcha.py --manual` for manual slider completion via Playwright CLI
