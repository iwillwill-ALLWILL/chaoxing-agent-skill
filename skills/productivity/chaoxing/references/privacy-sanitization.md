# Privacy Sanitization Guide

When sharing 学习通 automation configurations, scripts, or session logs publicly, ensure all personal data is removed.

## What to ALWAYS Remove

### Personal Identity
- Real name (姓名)
- Student ID (学号)
- Class/grade info (班级)
- University name

### Account Credentials
- `_uid` / `UID` cookie values
- `xxtenc` session tokens
- `uf` encrypted fingerprints
- `enc` / `standardEnc` URL parameters
- Any `token=` query parameters

### Course-Specific IDs
- `courseId` values (replace with `YOUR_COURSE_ID`)
- `clazzId` / `classId` values (replace with `YOUR_CLASS_ID`)
- `workId` / `answerId` values
- `cpi` values (session-specific)
- Exam `paperId` values

### Third-Party Keys
- Capsolver API keys (`CAP-...`)
- Any `clientKey` or `apiKey` values in scripts
- CAPTCHA `captchaId` values

### Scores and Answers
- Specific exam scores
- Actual answer content (essay text, code, accounting entries)
- "我的答案" content from detail pages

### Local File Paths
- Absolute paths containing usernames (`C:\Users\xxx\...`, `/home/xxx/...`)
- Replace with `~` or `$HOME` notation

## What is Safe to Share

- URL **patterns** (not specific URLs with IDs)
- Page structure analysis (CSS selectors, DOM hierarchy)
- Workflow descriptions and automation logic
- Reliability patterns and pitfall descriptions
- JavaScript code snippets (with placeholder IDs)
- Course **names** (if not uniquely identifying)
- Error messages from the platform (generic platform behavior)

## Sanitization Checklist

Before committing or publishing:

- [ ] Grep for your real name, student ID, university name
- [ ] Grep for `courseid=`, `courseId=`, `clazzid=`, `classId=`, `cpi=`
- [ ] Grep for `workId=`, `answerId=`, `enc=`, `token=`
- [ ] Grep for `CAP-`, `sk-`, `apiKey`, `clientKey`
- [ ] Grep for `captchaId`, `captchaCaptchaId`
- [ ] Grep for absolute paths (`C:\Users\`, `/home/`)
- [ ] Check JSON files for `.score` fields
- [ ] Check for email addresses
- [ ] Verify all URLs use placeholders (not real IDs)

## Placeholder Convention

Use consistent placeholders:
- `YOUR_COURSE_ID` — for course IDs
- `YOUR_CLASS_ID` — for class IDs
- `YOUR_CPI` — for cpi values
- `YOUR_CAPSOLVER_KEY` — for Capsolver API key
- `{courseId}` / `{classId}` — in URL templates
- `XXXX` or `...` — for partially redacted values needing format hints
