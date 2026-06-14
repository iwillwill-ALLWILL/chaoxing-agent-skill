# Reliability Pitfalls Catalog

Every pitfall below was encountered in real usage and has a verified fix. These are the patterns that separate "looks like it worked" from "actually worked."

---

## Pitfall 1: Empty Single-Choice Answers After Submit

**Symptom**: After batch-answering and submitting, the result page shows `我的答案:` blank for most single-choice questions. Multi-select answers saved correctly.

**Root Cause**: `.answerBg.click()` triggers an AJAX call to save the answer server-side. When 40+ questions are answered in a tight loop, ~40 AJAX calls fire simultaneously. Submitting immediately after answering means the server hasn't received most of them yet.

**Detection**: Exam detail page shows many empty `我的答案:` entries.

**Fix**: Wait 5 seconds after answering before submitting. Monitor `jQuery.active` if available:

```javascript
// After batch-answering all questions:
// DO NOT submit immediately!

// Option A: Simple wait
setTimeout(function() {
  finalSubmit();
}, 5000);

// Option B: Wait for AJAX drain (more robust)
async function waitForAjax(maxMs) {
  var start = Date.now();
  while (window.jQuery && jQuery.active > 0 && Date.now() - start < maxMs) {
    await new Promise(r => setTimeout(r, 80));
  }
  await new Promise(r => setTimeout(r, 120));
}
await waitForAjax(5000);
// Now submit
```

---

## Pitfall 2: Stale DOM References (Only Q1 Gets Answered)

**Symptom**: After batch-clicking answers in a loop, only the first question is answered. All other questions appear empty on the detail page.

**Root Cause**: Caching `document.querySelectorAll('div.questionLi')` into a NodeList before clicking. The first `.answerBg.click()` triggers DOM mutations that invalidate subsequent element references in the cached list.

**Detection**: Hidden input count after injection is 1 instead of total questions.

**Fix**: Collect question IDs first, then re-query each via `document.getElementById()`:

```javascript
// ❌ WRONG — cached references go stale:
var qs = document.querySelectorAll('div.questionLi');
for (var i = 0; i < qs.length; i++) {
  qs[i].querySelector('.answerBg').click(); // qs[i] may be stale after first click
}

// ✅ RIGHT — re-query fresh each time:
var qs = document.querySelectorAll('div.questionLi');
var ids = [];
for (var i = 0; i < qs.length; i++) ids.push(qs[i].id);

for (var i = 0; i < ids.length; i++) {
  var q = document.getElementById(ids[i]); // FRESH reference
  if (!q) continue;
  q.querySelector('.answerBg').click();
}
```

---

## Pitfall 3: CSS-Only Verification (Fake Success)

**Symptom**: After answering, all questions show `check_answer` CSS class (visual checkmark). Hidden input shows "0" or empty. Submit returns low score.

**Root Cause**: Clicking `span[data]` directly adds CSS class `check_answer` for visual feedback, but does NOT update the hidden `<input id="answer{qid}">`. `finalSubmit()` reads hidden inputs, not CSS classes.

**Detection**: `document.querySelector('input[id^=answer]').value === '0'` despite visual checkmark.

**Fix**: Always call the page's handler functions (`saveSingleSelect` / `clickSaveMultiSelect`) on the `.answerBg` div, or use `bg.click()` which triggers the inline `onclick`. Verify hidden inputs, not CSS:

```javascript
// ✅ Verify by hidden input value (NOT CSS class)
var ok = 0;
document.querySelectorAll('div.questionLi').forEach(function(q) {
  var hi = q.querySelector('input[id^=answer]');
  if (hi && hi.value && hi.value !== '0') ok++;
});
// Expected: ok === totalQuestions
```

---

## Pitfall 4: QID Randomization on Retake

**Symptom**: Retake answers map to wrong questions. Detail page shows incorrect or empty answers.

**Root Cause**: Each exam retake generates completely new QIDs. Hardcoded QID arrays from a previous attempt silently fail — answers appear visually selected (CSS) but hidden inputs stay empty because the QIDs don't match.

**Detection**: Hidden input count is 0 after answering despite visible checkmarks.

**Fix**: Always collect QIDs from the CURRENT page in DOM order, map answers by index:

```javascript
// ✅ Collect QIDs fresh every time
var singleQids = [], multiQids = [];
document.querySelectorAll('.answerBg').forEach(function(bg) {
  var oc = bg.getAttribute('onclick') || '';
  var m1 = oc.match(/saveSingleSelect\(this,\s*'([^']+)'\)/);
  var m2 = oc.match(/clickSaveMultiSelect\(this,\s*'([^']+)'\)/);
  if (m1 && !singleQids.includes(m1[1])) singleQids.push(m1[1]);
  if (m2 && !multiQids.includes(m2[1])) multiQids.push(m2[1]);
});

// Map answers by INDEX (0-based)
var answers = {};
for (var i = 0; i < singleQids.length; i++) answers[singleQids[i]] = singleAnswerLetters[i];
for (var i = 0; i < multiQids.length; i++) answers[multiQids[i]] = multiAnswerLetters[i];

// Never hardcode: answers['885502694'] = 'B'; ❌
```

---

## Pitfall 5: Multi-Select Start Offset

**Symptom**: Multi-select answers appear on wrong questions or don't save.

**Root Cause**: The hidden `<input name="start">` value for multi-select questions is NOT 0-based within the multi-select section. It's the 0-based index across ALL question types combined.

**Example**: 60 single-choice questions → multi-select `start` values are 60–79, NOT 0–19.

**Fix**: Query the first few multi-select questions to determine the offset:

```javascript
var firstMultiStart = -1;
document.querySelectorAll('div.questionLi').forEach(function(q) {
  var ti = q.querySelector('input[name^="type"]');
  if (ti && ti.value === '1' && firstMultiStart < 0) {
    firstMultiStart = parseInt(q.querySelector('input[name="start"]').value);
  }
});
// multiAnswers[startIdx - firstMultiStart] or multiAnswers[startIdx - singleCount]
```

---

## Pitfall 6: False Status Matches from Script Templates

**Symptom**: `fetch()` returns HTML that appears to contain "已完成" or "待做" when the page actually has no exams.

**Root Cause**: The exam-list HTML contains JavaScript template strings (I18N config) with status keywords. Text-extracting the full HTML without stripping scripts gives false positives.

**Fix**: Strip all `<script>...</script>` blocks before keyword matching:

```javascript
var clean = html.replace(/<script[\s\S]*?<\/script>/g, '');
var text = clean.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
var hasNoExam = text.indexOf('暂无考试') > -1;
```

---

## Pitfall 7: Expired Homework ("未交" ≠ Submittable)

**Symptom**: Homework shows "未交" status but clicking the entry URL loads a view-only page with "查看详情" instead of an editor.

**Root Cause**: "未交" only means "never submitted", not "can still submit". The deadline may have passed.

**Detection**: Check for "已过期" text in the homework list item, or "查看详情" instead of "提交" on the task page.

**Fix**: Before attempting submission, classify the task page:

```javascript
async function classifyTask(taskUrl) {
  var resp = await fetch(taskUrl, {credentials: 'include', redirect: 'follow'});
  var html = await resp.text();
  var doc = new DOMParser().parseFromString(html, 'text/html');
  doc.querySelectorAll('script,style').forEach(n => n.remove());
  var text = (doc.body?.innerText || '').replace(/\s+/g, ' ').trim();
  if (resp.url.includes('/work/prompt') || /提交成功|等待教师批阅/.test(text))
    return 'submitted';
  if (resp.url.includes('/work/view') || /作业详情|已过期|已截止/.test(text))
    return 'closed';
  if (resp.url.includes('/work/dowork') || /暂时保存|提交 作业|作业作答/.test(text))
    return 'submittable';
  return 'unknown';
}
```

---

## Pitfall 8: `saveSingleSelect` Not Globally Accessible

**Symptom**: `typeof saveSingleSelect === "undefined"` on the exam page. Calling it directly throws ReferenceError.

**Root Cause**: In many exam versions, `saveSingleSelect` is defined in a closure, not on `window`.

**Fix**: Use `bg.click()` which triggers the inline `onclick="saveSingleSelect(this,'qid')"` handler:

```javascript
// ✅ Works even when function isn't global
var bg = q.querySelector('.answerBg');
bg.click();

// ❌ Fails when function is in closure
saveSingleSelect(bg, qid);
```

---

## Pitfall 9: CAPTCHA Entry Without Real Validate

**Symptom**: Bypassing CAPTCHA with `captchaCheck=0` + `jumpExam('false')` navigates to exam page but shows "无权限访问".

**Root Cause**: The server validates the CAPTCHA token (`validate`) in the `checkAction` AJAX call. Skipping the CAPTCHA means no valid `enc` token, so exam content is blocked.

**Fix for first entry**: Must complete the CAPTCHA pipeline (Capsolver or manual). No bypass possible.

**Fix for retakes**: `reVersionReTest` AJAX may bypass CAPTCHA checks. Setting `captchaCheck=0` + `jumpExam('true')` can work for retakes specifically.

---

## Pitfall 10: topreview Viewport Answer Loss

**Symptom**: After answering in `topreview()` mode and navigating (clicking "next question" or changing view), some answers are lost.

**Root Cause**: Hidden inputs for questions not in the current viewport may be cleared when the page refreshes a section.

**Fix**: Never navigate away from `topreview()` after answering. Submit directly from the `topreview` page:

```javascript
topreview();
setTimeout(function() {
  // Answer all questions...
  // Submit directly — do NOT click "next question"
  document.querySelector('.completeBtn')?.click();
}, 2000);
```

---

## Summary: The Verification Golden Rule

**Never trust visual state. Always verify hidden inputs.**

```javascript
// The one check that matters:
var inputValue = document.getElementById('answer' + qid)?.value;
// inputValue must be 'A' or 'AB' (answer letters), NOT '0' or ''
```
