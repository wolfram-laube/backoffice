#!/usr/bin/env python3
"""
GitLab CI Flaky Ledger Bot (stdlib only)

Purpose:
- When CI classification marks a run as flaky (first run failed, rerun passed) on main branch pushes,
  record the occurrence in a single "ledger" issue (deduped).
- If flaky occurrences reach a threshold, create/update a "flaky escalated" issue for visibility.

Required env:
  - GITLAB_TOKEN
  - CI_API_V4_URL
  - CI_PROJECT_ID
  - CI_PROJECT_PATH
  - CI_COMMIT_BRANCH
  - CI_COMMIT_SHORT_SHA
  - CI_PIPELINE_URL
  - CI_JOB_URL
  - CI_JOB_NAME
  - CI_PIPELINE_ID

From classification (dotenv):
  - CI_BOT_CONFIRMED_FAILURE (must be 0)
  - CI_BOT_FLAKY (must be 1)

Optional env:
  - CI_BOT_FLAKY_LEDGER_FINGERPRINT  (default: "clarissa-ci-flaky-ledger:<branch>")
  - CI_BOT_FLAKY_ESCALATE_AFTER_N    (default: 3)
  - CI_BOT_FLAKY_ESCALATION_LABELS   (default: "ci,ci-flaky-suspected")
  - CI_BOT_FLAKY_ESCALATION_TITLE    (default: "Flaky CI suspected on {project} ({branch})")
"""

from __future__ import annotations
import json, os, sys, urllib.parse, urllib.request
from typing import Any, Dict, List, Optional


def env(name: str, default: Optional[str] = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        return default or ""
    return v


def api_request(method: str, url: str, token: str, data: Optional[dict] = None) -> Any:
    headers = {
        "PRIVATE-TOKEN": token,
        "Content-Type": "application/json",
        "User-Agent": "clarissa-ci-flaky-ledger-bot/1.0",
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url=url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} for {url}: {msg}") from e


def project_url(api: str, project_id: str, path: str) -> str:
    return f"{api}/projects/{urllib.parse.quote(project_id, safe='')}{path}"


def marker(kind: str, fingerprint: str) -> str:
    return f"<!-- {kind}:{fingerprint} -->"


def find_issue(api: str, project_id: str, token: str, search: str) -> Optional[Dict[str, Any]]:
    q = urllib.parse.urlencode({"state": "opened", "search": search, "per_page": 20})
    url = project_url(api, project_id, f"/issues?{q}")
    issues = api_request("GET", url, token) or []
    return issues[0] if isinstance(issues, list) and issues else None


def create_issue(api: str, project_id: str, token: str, title: str, description: str, labels: List[str]) -> Dict[str, Any]:
    url = project_url(api, project_id, "/issues")
    data: Dict[str, Any] = {"title": title, "description": description}
    if labels:
        data["labels"] = ",".join(labels)
    return api_request("POST", url, token, data)


def add_note(api: str, project_id: str, token: str, issue_iid: int, body: str) -> Any:
    url = project_url(api, project_id, f"/issues/{issue_iid}/notes")
    return api_request("POST", url, token, {"body": body})


def list_notes(api: str, project_id: str, token: str, issue_iid: int) -> List[Dict[str, Any]]:
    q = urllib.parse.urlencode({"per_page": 100, "sort": "desc", "order_by": "created_at"})
    url = project_url(api, project_id, f"/issues/{issue_iid}/notes?{q}")
    notes = api_request("GET", url, token) or []
    return notes if isinstance(notes, list) else []


def main() -> int:
    confirmed = env("CI_BOT_CONFIRMED_FAILURE", "0").strip() == "1"
    flaky = env("CI_BOT_FLAKY", "0").strip() == "1"
    if confirmed or not flaky:
        print("Not a flaky event; skipping.")
        return 0

    token = env("GITLAB_TOKEN")
    api = env("CI_API_V4_URL", "https://gitlab.com/api/v4")
    project_id = env("CI_PROJECT_ID")
    if not token or not project_id:
        print("Missing GITLAB_TOKEN or CI_PROJECT_ID", file=sys.stderr)
        return 2

    branch = env("CI_COMMIT_BRANCH", "unknown-branch")
    project_path = env("CI_PROJECT_PATH", "unknown/project")
    sha = env("CI_COMMIT_SHORT_SHA", "unknown")
    pipeline_url = env("CI_PIPELINE_URL", "")
    job_url = env("CI_JOB_URL", "")
    job = env("CI_JOB_NAME", "tests")
    pipeline_id = env("CI_PIPELINE_ID", "")

    ledger_fp = env("CI_BOT_FLAKY_LEDGER_FINGERPRINT", f"clarissa-ci-flaky-ledger:{branch}")
    ledger_mark = marker("clarissa-ci-flaky-ledger", ledger_fp)

    # 1) Find/create ledger issue
    ledger = find_issue(api, project_id, token, ledger_mark)
    if not ledger:
        title = f"CI flaky ledger ({project_path}:{branch})"
        desc = f"{ledger_mark}\nThis issue tracks flaky CI occurrences on `{project_path}` `{branch}`.\n"
        ledger = create_issue(api, project_id, token, title, desc, ["ci"])

    ledger_iid = int(ledger["iid"])
    note_mark = marker("clarissa-ci-flaky-ledger-note", f"{branch}:{job}")
    note = (
        f"{note_mark}\n"
        f"🟡 Flaky CI observed.\n\n"
        f"- Branch: `{branch}`\n"
        f"- Job: `{job}`\n"
        f"- Commit: `{sha}`\n"
        f"- Pipeline: {pipeline_url}\n"
        f"- Job URL: {job_url}\n"
    )
    add_note(api, project_id, token, ledger_iid, note)

    # 2) Count ledger notes for this job+branch marker (best-effort last 100)
    notes = list_notes(api, project_id, token, ledger_iid)
    count = sum(1 for n in notes if note_mark in (n.get("body") or ""))

    threshold = int(env("CI_BOT_FLAKY_ESCALATE_AFTER_N", "3") or "3")
    print(f"Ledger count for {branch}:{job} is {count} (threshold {threshold}).")

    if count < threshold:
        return 0

    # 3) Escalate: create/update a dedicated flaky issue (deduped)
    esc_fp = f"clarissa-ci-flaky:{job}:{branch}"
    esc_mark = marker("clarissa-ci-flaky", esc_fp)
    esc = find_issue(api, project_id, token, esc_mark)
    labels = [s.strip() for s in env("CI_BOT_FLAKY_ESCALATION_LABELS", "ci,ci-flaky-suspected").split(",") if s.strip()]
    title_tpl = env("CI_BOT_FLAKY_ESCALATION_TITLE", "Flaky CI suspected on {project} ({branch})")
    title = title_tpl.format(project=project_path, branch=branch)
    desc = (
        f"{esc_mark}\n"
        f"Flaky CI has been observed **{count}** times for `{project_path}` `{branch}` job `{job}`.\n\n"
        f"Latest:\n- Commit: `{sha}`\n- Pipeline: {pipeline_url}\n- Job: {job_url}\n\n"
        f"See ledger issue !{ledger_iid} for history.\n"
    )
    if esc:
        add_note(api, project_id, token, int(esc["iid"]), desc)
        print(f"Updated flaky escalation issue !{esc['iid']}.")
    else:
        created = create_issue(api, project_id, token, title, desc, labels)
        print(f"Created flaky escalation issue !{created.get('iid')}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
