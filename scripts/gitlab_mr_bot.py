#!/usr/bin/env python3
"""
Post a helpful MR comment based on CI artifacts.

Design goals:
- Never fail the pipeline (best-effort bot).
- If no token or no MR context, exit 0 without doing anything harmful.
- If artifacts are missing, just omit those sections.

Expected inputs (optional):
- ci_classify.env (dotenv) produced by ci_classify job
- reports/mr_report.md (optional)
- tests/governance/impact.md (optional)
- tests/golden/summary.md (optional)
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Optional


MAX_COMMENT_CHARS = 90_000  # keep well below GitLab note limits


def env(name: str, default: str = "") -> str:
    v = os.getenv(name)
    return v if v not in (None, "") else default


def read_text_if_exists(path: str, max_bytes: int = 200_000) -> Optional[str]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    data = p.read_bytes()
    if len(data) > max_bytes:
        # ASCII-only marker: byte literals cannot contain unicode like “…” (U+2026)
        data = data[:max_bytes] + b"\n\n...(truncated)...\n"
    return data.decode("utf-8", errors="replace")


def parse_dotenv(path: str) -> Dict[str, str]:
    """
    Very small dotenv parser:
    KEY=VALUE lines, ignores comments and blank lines.
    """
    out: Dict[str, str] = {}
    p = Path(path)
    if not p.exists():
        return out
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def gitlab_api_url(base: str, project_id: str, mr_iid: str, path: str) -> str:
    pid = urllib.parse.quote(project_id, safe="")
    return f"{base}/projects/{pid}/merge_requests/{mr_iid}{path}"


def api_post_note(
    api_base: str,
    project_id: str,
    mr_iid: str,
    pat_token: str,
    job_token: str,
    body: str,
) -> bool:
    url = gitlab_api_url(api_base, project_id, mr_iid, "/notes")
    payload = json.dumps({"body": body}).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "clarissa-ci-mr-bot/1.0",
    }

    # Deterministic auth selection:
    # - Prefer PAT via PRIVATE-TOKEN if provided
    # - Else try CI_JOB_TOKEN via JOB-TOKEN
    if pat_token:
        headers["PRIVATE-TOKEN"] = pat_token
    elif job_token:
        headers["JOB-TOKEN"] = job_token
    else:
        print("[mr-bot] No token available for API call.")
        return False

    req = urllib.request.Request(url=url, data=payload, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            _ = resp.read()
        return True
    except urllib.error.HTTPError as e:
        print(f"[mr-bot] GitLab API HTTPError {e.code}: {e.reason}")
        try:
            print(e.read().decode("utf-8", errors="replace"))
        except Exception:
            pass
        return False
    except Exception as e:
        print(f"[mr-bot] GitLab API request failed: {type(e).__name__}: {e}")
        return False


def build_comment() -> str:
    classify_env_path = env("CI_BOT_CLASSIFY_ENV_PATH", "ci_classify.env")
    report_path = env("CI_BOT_MR_REPORT_PATH", "reports/mr_report.md")
    governance_path = env("CI_BOT_GOVERNANCE_IMPACT_PATH", "tests/governance/impact.md")
    snapshot_summary_path = env("CI_BOT_SNAPSHOT_SUMMARY_PATH", "tests/golden/summary.md")

    classify = parse_dotenv(classify_env_path)

    lines: list[str] = []
    lines.append("## 🤖 CI report (CLARISSA)")
    lines.append("")

    lines.append("### Classification")
    if classify:
        for key in [
            "CI_CLASSIFICATION",
            "CI_FLAKY_SCORE",
            "CI_PRIMARY_FAILURE",
            "CI_RERUN_EXIT_CODE",
            "CI_RECOMMENDATION",
        ]:
            if key in classify:
                lines.append(f"- **{key}**: `{classify[key]}`")
    else:
        lines.append("- _(no classification env found; skipping)_")
    lines.append("")

    lines.append("### Governance impact")
    gov = read_text_if_exists(governance_path)
    if gov:
        lines.append(gov.strip())
    else:
        lines.append("- _(no governance report artifact found; skipping)_")
    lines.append("")

    lines.append("### Snapshot diffs")
    snap = read_text_if_exists(snapshot_summary_path)
    if snap:
        lines.append(snap.strip())
    else:
        lines.append("- _(no snapshot summary found; skipping)_")
    lines.append("")

    lines.append("### MR report")
    rpt = read_text_if_exists(report_path)
    if rpt:
        lines.append(rpt.strip())
    else:
        lines.append("- _(no MR report artifact found; skipping)_")
    lines.append("")

    pipeline_url = env("CI_PIPELINE_URL", "")
    job_url = env("CI_JOB_URL", "")
    if pipeline_url or job_url:
        lines.append("---")
        meta: list[str] = []
        if pipeline_url:
            meta.append(f"[Pipeline]({pipeline_url})")
        if job_url:
            meta.append(f"[Job]({job_url})")
        lines.append(" · ".join(meta))

    body = "\n".join(lines).strip() + "\n"
    if len(body) > MAX_COMMENT_CHARS:
        body = body[:MAX_COMMENT_CHARS] + "\n\n...(truncated overall comment)...\n"
    return body


def main() -> int:
    api = env("CI_API_V4_URL", "https://gitlab.com/api/v4")
    project_id = env("CI_PROJECT_ID", "")
    mr_iid = env("CI_MERGE_REQUEST_IID", "")

    pat = env("GITLAB_TOKEN", "")
    job = env("CI_JOB_TOKEN", "")

    if not project_id or not mr_iid:
        print("[mr-bot] Not in MR context (missing CI_PROJECT_ID or CI_MERGE_REQUEST_IID). Skipping.")
        return 0

    if not pat and not job:
        print("[mr-bot] Missing token (GITLAB_TOKEN/CI_JOB_TOKEN). Skipping MR comment.")
        return 0

    body = build_comment()
    ok = api_post_note(api, project_id, mr_iid, pat, job, body)
    if ok:
        print("[mr-bot] Posted MR comment.")
    else:
        print("[mr-bot] Could not post MR comment (non-fatal).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
