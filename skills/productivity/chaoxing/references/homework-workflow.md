# Homework Workflow Reference

## Page Structure

学习通 homework pages have two main types:

### Type A: Rich-Text Editor (UEditor)

Used for essay/attachment homework. Single `<textarea>` with a rich-text editor overlay.

**Detection**: `document.querySelector('#ueditor_0') !== null`

**UEditor API** (from the page's global scope):
```javascript
// Get editor instance
var editor = UE.getEditor('answer' + qid);

// Set content
editor.setContent('<p>Your answer HTML here</p>');

// Sync to hidden textarea
editor.sync();

// Alternative: set iframe body directly
var iframe = document.querySelector('#ueditor_0');
var doc = iframe.contentDocument || iframe.contentWindow.document;
doc.body.innerHTML = '<p>Answer...</p>';
var ta = document.querySelector('textarea');
if (ta) ta.value = doc.body.innerHTML;
```

### Type B: Quiz/Test (Clickable Options)

Same as exam questions — `.questionLi` containers with `.answerBg` elements.

**Detection**: `document.querySelectorAll('.answerBg').length > 10`

## Submission Pipeline

### Step 1: Fill Content

```javascript
// For Type A:
var iframe = document.querySelector('#ueditor_0');
if (iframe) {
  var doc = iframe.contentDocument || iframe.contentWindow.document;
  doc.body.innerHTML = '<p>Completed answer content.</p>';
  // Sync to textarea
  var ta = document.querySelector('textarea');
  if (ta) ta.value = doc.body.innerHTML;
  // Also sync via editor API if available
  try {
    UE.getEditor('answer' + qid).sync();
  } catch(e) {}
}

// For Type B:
// Same as exam answer injection pattern (see SKILL.md Workflow 4)
```

### Step 2: Fill Hidden Form Fields

```javascript
// Some homework types require filling questionIds:
var qids = [...document.querySelectorAll('[id^="answertype"]')]
  .map(x => x.id.replace('answertype', '')).filter(Boolean);
document.querySelector('#questionIds').value = qids.join(',') + (qids.length ? ',' : '');
```

### Step 3: Trigger Submit

The submit button is `<a role="button">` with text "提交":

```javascript
// Find and click the submit button
document.querySelectorAll('a').forEach(function(a) {
  if (a.innerText?.trim() === '提交' && a.getBoundingClientRect().height > 0)
    a.click();
});
```

### Step 4: Confirm Dialog

After clicking submit, a modal dialog appears with a second "提交" button:

```javascript
// Wait for dialog, then confirm
setTimeout(function() {
  document.querySelectorAll('a, button, div[onclick]').forEach(function(b) {
    if (b.innerText?.trim() === '提交' && b.getBoundingClientRect().height > 0)
      b.click();
  });
}, 1000);
```

### Step 5: Verify Submission

```javascript
// After submit, page should navigate to /work/prompt
// with "提交成功" / "等待教师批阅" text

// For programmatic verification:
var text = document.body.innerText;
var submitted = text.includes('提交成功') || text.includes('等待教师批阅');
```

## Attachment Upload

### Extract Upload URL and Token

```javascript
var form = document.querySelector('#submitForm');
var action = form?.getAttribute('action');
var token = document.querySelector('input[name="token"]')?.value;
var uid = document.querySelector('#userId')?.value;

// Standard upload endpoint:
var uploadUrl = 'https://mooc1.chaoxing.com/upload-ans/ueditorupload/attachment?uploadtype=work';
```

### Upload via FormData

```javascript
// Using fetch from the page context:
async function uploadFile(fileName, fileBlob, uploadUrl, token) {
  var formData = new FormData();
  formData.append('file', fileBlob, fileName);
  formData.append('token', token);
  // ... other required fields

  var resp = await fetch(uploadUrl, {
    method: 'POST',
    body: formData,
    credentials: 'include'
  });
  var result = await resp.json();
  // result.objectId is the uploaded file ID
  return result;
}
```

### Generate Attachment HTML

After upload, insert attachment HTML into the editor:

```javascript
var attachHtml = '' +
  '<div class="editor-iframe" contenteditable="false">' +
  '<iframe frameborder="0" scrolling="no" ' +
  'src="/ananas/common-modules/attachment/insertCloud.html" ' +
  'module="insertAttach" ' +
  'objectid="' + objectId + '" ' +
  'filename="' + fileName + '" ' +
  'filetype="' + fileType + '">' +
  '</iframe></div>';
```

## Task URL Pattern

```
Task entry: /mooc-ans/mooc2/work/task?courseId=X&classId=X&workId=X&answerId=X&enc=X
Redirects to: /mooc-ans/mooc2/work/dowork?courseId=X&...&standardEnc=X&enc=X
After submit: /mooc-ans/mooc2/work/prompt?courseId=X&...&enc=X
```

## Common Homework Answer Templates

### Accounting (会计分录) Template

```html
<p>（1）借：科目名称　金额</p>
<p>　　贷：科目名称　金额</p>
<p>（2）借：科目名称　金额</p>
<p>　　贷：科目名称　金额</p>
```

### Math Solution Template

```html
<p>解：</p>
<p>由已知条件得：...</p>
<p>∴ ...</p>
<p>故答案为：...</p>
```

### Essay/Report Template

```html
<h2 style="text-align:center;">标题</h2>
<p style="text-align:center;">姓名：XXX　学号：XXX　班级：XXX</p>
<p>&emsp;&emsp;正文内容...</p>
```

## Batch Classification Checklist

For each course, after scanning the homework list:

- [ ] For each "未交" item, fetch the task page to determine if submittable
- [ ] Check for "已过期" — expired tasks are view-only
- [ ] Check for "提交成功" / "等待教师批阅" — already submitted
- [ ] Check editor type (UEditor vs quiz) before attempting fill
- [ ] Verify submission by re-fetching the task page
