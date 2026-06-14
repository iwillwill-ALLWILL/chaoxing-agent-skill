#!/usr/bin/env python3
"""Verify homework/exam submission status via same-origin fetch.

For each task URL, fetches the page and classifies its status as:
- submitted_prompt: Already submitted (提交成功/等待教师批阅)
- submitted_view: Viewing submitted details (作业详情/已批阅)
- needs_submit: Editable and ready to submit (作业作答)
- closed/error: Cannot access or expired

Usage:
    python verify_submission.py <tab_id> <tasks.json> [output.json]

tasks.json format:
    [{"name": "Task Name", "url": "https://mooc1.chaoxing.com/mooc-ans/..."}, ...]
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from relay_helpers import js_eval


def verify_batch(tab_id: int, tasks: list) -> list:
    """Verify all tasks in one JS call using same-origin fetch."""
    tasks_json = json.dumps(tasks, ensure_ascii=False)
    code = f"""
    return (async function() {{
        var tasks = {tasks_json};
        var results = [];
        for (var i = 0; i < tasks.length; i++) {{
            var t = tasks[i];
            try {{
                var resp = await fetch(t.url, {{credentials: 'include', redirect: 'follow'}});
                var html = await resp.text();
                var doc = new DOMParser().parseFromString(html, 'text/html');
                doc.querySelectorAll('script,style').forEach(function(n) {{ n.remove(); }});
                var text = (doc.body && doc.body.innerText || '').replace(/\\s+/g, ' ').substring(0, 1800);

                var status = 'unknown';
                if (resp.url.indexOf('/work/prompt') > -1 || /提交成功|等待教师批阅/.test(text))
                    status = 'submitted_prompt';
                else if (resp.url.indexOf('/work/view') > -1 || /作业详情|我的答案|正确答案|已批阅|待批阅/.test(text))
                    status = 'submitted_view';
                else if (resp.url.indexOf('/work/dowork') > -1 || /暂时保存|提交 作业|作业作答/.test(text))
                    status = 'needs_submit';

                results.push({{
                    name: t.name,
                    course: t.course || '',
                    status: status,
                    finalUrl: resp.url,
                    title: doc.title,
                    text: text.substring(0, 300)
                }});
            }} catch(e) {{
                results.push({{name: t.name, course: t.course || '', status: 'error', error: String(e)}});
            }}
        }}
        return JSON.stringify(results);
    }})();
    """

    result = js_eval(tab_id, code, timeout_ms=60000, timeout=90)
    return json.loads(result)


def main():
    if len(sys.argv) < 3:
        print("Usage: python verify_submission.py <tab_id> <tasks.json> [output.json]")
        sys.exit(1)

    tab_id = int(sys.argv[1])
    tasks_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("verify_results.json")

    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    results = verify_batch(tab_id, tasks)

    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summary
    from collections import Counter
    status_counts = Counter(r["status"] for r in results)
    print(f"Total: {len(results)}, Status: {dict(status_counts)}")

    for r in results:
        if r["status"] == "needs_submit":
            print(f"  ⚠ NEEDS SUBMIT: {r.get('course')} / {r['name']}")
        elif r["status"] == "error":
            print(f"  ❌ ERROR: {r.get('course')} / {r['name']}: {r.get('error')}")


if __name__ == "__main__":
    main()
