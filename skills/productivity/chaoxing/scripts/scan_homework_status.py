#!/usr/bin/env python3
"""Batch-scan homework status across all courses using browser relay.

Reads a course inventory JSON file and uses same-origin fetch() calls
from a 学习通 page to check homework status for each course.

Usage:
    python scan_homework_status.py <relay_tab_id> <course_inventory.json> [output.json]
"""

import json
import sys
import time
from pathlib import Path

# Import relay helpers from the same directory
sys.path.insert(0, str(Path(__file__).parent))
from relay_helpers import js_eval, open_tab, close_tab, clean_html_text


def scan_course(tab_id: int, course: dict) -> dict:
    """Scan one course's homework list."""
    name = course.get("name", "Unknown")
    course_id = course["courseId"]
    class_id = course["clazzId"]
    cpi = course.get("cpi", "")

    # Homework list URL requires enc from course page — use the list URL if provided
    list_url = course.get("homeworkListUrl")
    if not list_url:
        return {"course": name, "error": "no_list_url"}

    # Use same-origin fetch from any mooc1 page
    code = f"""
    return (async function() {{
        try {{
            var resp = await fetch('{list_url}', {{credentials: 'include', redirect: 'follow'}});
            var html = await resp.text();
            var doc = new DOMParser().parseFromString(html, 'text/html');
            doc.querySelectorAll('script,style').forEach(function(n) {{ n.remove(); }});
            var text = (doc.body && doc.body.innerText || '').replace(/\\s+/g, ' ').trim();

            // Extract homework items from <li> elements
            var items = [];
            doc.querySelectorAll('li').forEach(function(li) {{
                var dataUrl = li.getAttribute('data');
                if (dataUrl) {{
                    var itemText = li.innerText.trim();
                    var lines = itemText.split('\\n').filter(function(l) {{ return l.trim(); }});
                    var name = lines[0] || '';
                    var status = 'unknown';
                    if (itemText.indexOf('未交') > -1) status = 'pending';
                    else if (itemText.indexOf('待批阅') > -1) status = 'submitted';
                    else if (itemText.indexOf('已完成') > -1) status = 'done';
                    else if (itemText.indexOf('已过期') > -1) status = 'expired';
                    items.push({{name: name, status: status, url: dataUrl, text: itemText.substring(0, 200)}});
                }}
            }});

            return JSON.stringify({{
                course: '{name}',
                courseId: '{course_id}',
                itemCount: items.length,
                hasNoHomework: text.indexOf('暂无作业') > -1,
                items: items,
                textPreview: text.substring(0, 500)
            }});
        }} catch(e) {{
            return JSON.stringify({{course: '{name}', error: String(e)}});
        }}
    }})();
    """

    result = js_eval(tab_id, code, timeout_ms=30000, timeout=45)
    return json.loads(result)


def main():
    if len(sys.argv) < 3:
        print("Usage: python scan_homework_status.py <tab_id> <course_inventory.json> [output.json]")
        print("  tab_id: A browser tab on any mooc1.chaoxing.com page")
        sys.exit(1)

    tab_id = int(sys.argv[1])
    inventory_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("homework_scan_results.json")

    courses = json.loads(inventory_path.read_text(encoding="utf-8"))
    results = []

    for course in courses:
        try:
            rec = scan_course(tab_id, course)
            print(f"  {rec.get('course')}: {rec.get('itemCount', 0)} items, noHomework={rec.get('hasNoHomework')}")
        except Exception as e:
            rec = {"course": course.get("name"), "error": str(e)}
            print(f"  ERROR {course.get('name')}: {e}")
        results.append(rec)

    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summary
    from collections import Counter
    all_items = [it for r in results for it in r.get("items", [])]
    status_counts = Counter(it["status"] for it in all_items)
    print(f"\nTotal courses: {len(results)}, Total items: {len(all_items)}")
    print(f"Status distribution: {dict(status_counts)}")

    pending = [it for it in all_items if it["status"] == "pending"]
    print(f"\nPending ({len(pending)}):")
    for it in pending:
        print(f"  [{it['status']}] {it['name']}")


if __name__ == "__main__":
    main()
