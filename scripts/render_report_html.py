#!/usr/bin/env python3
"""Render reports/mr_report.md into reports/mr_report.html (minimal renderer).

This is intentionally simple: headings, paragraphs, code fences, and tables are rendered roughly.
For production-grade rendering, swap in pandoc later.
"""
from __future__ import annotations
from pathlib import Path
import html

def main() -> int:
    md_path = Path("reports/mr_report.md")
    if not md_path.exists():
        raise SystemExit("reports/mr_report.md not found. Run generate_mr_report.py first.")
    md = md_path.read_text(encoding="utf-8").splitlines()

    out = []
    out.append("<!doctype html><html><head><meta charset='utf-8'>")
    out.append("<meta name='viewport' content='width=device-width, initial-scale=1'>")
    out.append("<title>CLARISSA MR Report</title>")
    out.append("<style>body{font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:980px;margin:24px auto;padding:0 16px;line-height:1.35}"
               "code,pre{font-family:ui-monospace,Menlo,Consolas,monospace}pre{padding:12px;border:1px solid #ddd;border-radius:8px;overflow:auto}"
               "table{border-collapse:collapse;width:100%;margin:12px 0}td,th{border:1px solid #ddd;padding:8px}"
               "h1,h2,h3{margin-top:22px}hr{border:none;border-top:1px solid #ddd;margin:22px 0}</style></head><body>")
    in_code = False
    in_table = False

    def flush_table(rows):
        if not rows: return
        out.append("<table>")
        # header
        head = rows[0]
        out.append("<tr>" + "".join(f"<th>{html.escape(c.strip())}</th>" for c in head) + "</tr>")
        for r in rows[2:]:  # skip separator line
            out.append("<tr>" + "".join(f"<td>{html.escape(c.strip())}</td>" for c in r) + "</tr>")
        out.append("</table>")

    table_rows = []

    for line in md:
        if line.startswith("```"):
            if not in_code:
                in_code = True
                out.append("<pre><code>")
            else:
                in_code = False
                out.append("</code></pre>")
            continue

        if in_code:
            out.append(html.escape(line) + "\n")
            continue

        if line.strip() == "---":
            if table_rows:
                flush_table(table_rows)
                table_rows = []
            out.append("<hr/>")
            continue

        if line.startswith("|") and "|" in line[1:]:
            # table row
            cols = [c for c in line.strip().strip("|").split("|")]
            table_rows.append(cols)
            continue
        else:
            if table_rows:
                flush_table(table_rows)
                table_rows = []

        if line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
        elif line.strip() == "":
            out.append("<p></p>")
        elif line.startswith("- "):
            # naive list: wrap each item individually
            out.append(f"<p>• {html.escape(line[2:].strip())}</p>")
        else:
            out.append(f"<p>{html.escape(line)}</p>")

    if table_rows:
        flush_table(table_rows)

    out.append("</body></html>")
    Path("reports").mkdir(parents=True, exist_ok=True)
    Path("reports/mr_report.html").write_text("\n".join(out), encoding="utf-8")
    print("Wrote reports/mr_report.html")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
