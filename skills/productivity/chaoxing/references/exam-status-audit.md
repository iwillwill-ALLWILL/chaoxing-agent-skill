# Exam Status Audit Reference

## Batch Scanning Architecture

To audit exam status across all courses efficiently, use same-origin `fetch()` from any `mooc1.chaoxing.com` page. This avoids opening a browser tab per course (~1s vs ~10s).

## Course Inventory

Maintain a JSON config with courseId, clazzId, and cpi for each course:

```json
[
  {"name": "Course Name", "courseId": "XXXXXXXXX", "clazzId": "XXXXXXXXX", "cpi": "XXXXXXXXX"},
  ...
]
```

The `cpi` value is typically constant across courses for a given student session. Extract it once from any exam-list URL.

## Exam List URL Pattern

```
https://mooc1.chaoxing.com/exam-ans/mooc2/exam/exam-list?courseid={id}&clazzid={id}&cpi={cpi}&ut=s
```

Note: This URL works without an `enc` parameter — making it ideal for batch scanning.

## Batch Fetch Script

```javascript
async function scanAllExams(courses) {
  var results = [];
  for (var c of courses) {
    var url = 'https://mooc1.chaoxing.com/exam-ans/mooc2/exam/exam-list?courseid='
      + c.courseId + '&clazzid=' + c.clazzId + '&cpi=' + c.cpi + '&ut=s';
    try {
      var resp = await fetch(url, {credentials: 'include'});
      var html = await resp.text();

      // Strip scripts to avoid false keyword matches
      var clean = html.replace(/<script[\s\S]*?<\/script>/g, '');
      var text = clean.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();

      // Extract exam entries
      var exams = [];
      // Each exam row has: exam name, status (待做/已完成/已过期), score, deadline
      // Parse from text or HTML structure

      var hasNoExam = text.indexOf('暂无考试') > -1;
      results.push({
        course: c.name,
        courseId: c.courseId,
        hasNoExam: hasNoExam,
        examCount: exams.length,
        exams: exams,
        textPreview: text.substring(0, 300)
      });
    } catch(e) {
      results.push({course: c.name, error: String(e)});
    }
  }
  return results;
}
```

## Exam Entry Extraction

From the exam-list HTML, each exam row contains:

```html
<div class="exam-list-item" onclick="goTest(...)">
  <span class="exam-name">Exam Name</span>
  <span class="exam-status">待做</span>
  <span class="exam-deadline">剩余 210 小时 48 分钟</span>
</div>
```

**Extract goTest() parameters:**
```javascript
var matches = html.match(/goTest\('(\d+)','(\d+)',(\d+),'([^']*)','(\d+)',(\w+),'([^']*)'\)/g);
matches.forEach(function(m) {
  var parts = m.match(/goTest\('(\d+)','(\d+)',(\d+),'([^']*)','(\d+)',(\w+),'([^']*)'\)/);
  // parts[1]=courseId, parts[2]=examId, parts[3]=?, parts[4]=endTime,
  // parts[5]=paperId, parts[6]=?, parts[7]=enc
});
```

## Status Classification

| Text Pattern | Status | Action |
|---|---|---|
| `待做` | Pending | Can enter and complete |
| `未开始` | Not started | Can enter and complete |
| `已完成` | Completed | View details only |
| `已过期` | Expired | Cannot access |
| `暂无考试` | No exams | Skip course |

## Score Extraction

From exam list or detail page:
```javascript
var scoreMatch = text.match(/(\d+(?:\.\d+)?)\s*分/);
var score = scoreMatch ? parseFloat(scoreMatch[1]) : null;
```

## Retake Detection

```javascript
// Check for retake button in exam list
var retakeBtn = document.querySelector('[onclick*="reTest"]');
var retakeAvailable = retakeBtn !== null;

// Check remaining time
var timeMatch = text.match(/剩余\s*(\d+)\s*小时/);
var hoursRemaining = timeMatch ? parseInt(timeMatch[1]) : 0;

// Retake URL pattern:
// /exam-ans/exam/test/examcode/examnotes?courseId=X&...&reset=true
```

## Auto-Retake Decision Logic

```javascript
function shouldRetake(exam) {
  // Thresholds (configurable)
  var PASS_THRESHOLD = 60;
  var HIGH_THRESHOLD = 90;

  if (exam.score === null) return {retake: false, reason: 'no_score'};
  if (exam.score >= HIGH_THRESHOLD) return {retake: false, reason: 'already_high'};
  if (!exam.retakeAvailable) return {retake: false, reason: 'no_retake_button'};
  if (exam.hoursRemaining <= 0) return {retake: false, reason: 'time_expired'};

  return {retake: true, reason: 'low_score', score: exam.score};
}
```

## Answer Verification (Post-Submit)

After submitting or retaking, verify answers are non-empty:

```javascript
// On exam detail/view page:
var emptyAnswers = [];
document.querySelectorAll('.questionLi').forEach(function(q, i) {
  var answerText = q.innerText;
  // Match "我的答案:" followed by content
  var match = answerText.match(/我的答案:\s*(.*)/);
  if (match && (!match[1] || match[1].trim() === '')) {
    emptyAnswers.push({index: i, question: q});
  }
});
var hasEmptyAnswers = emptyAnswers.length > 0;
```

## Report Format

After scanning, produce a structured report:

```json
{
  "totalCourses": 15,
  "coursesWithExams": 8,
  "totalExams": 22,
  "pending": 3,
  "completed": 14,
  "expired": 5,
  "lowScoreRetakeable": [
    {"course": "...", "exam": "...", "score": 48, "hoursRemaining": 210}
  ],
  "unfixable": [
    {"course": "...", "exam": "...", "reason": "no_retake_button"}
  ]
}
```
