#!/usr/bin/env python3
"""
GitLab CI Recovery Bot (stdlib only)

On successful pipelines (main branch pushes), find the deduped CI failure issue and:
- add a "recovered" comment
- optionally add a "flaky" label and/or close the issue

Required env:
  - GITLAB_TOKEN
  - CI_API_V4_URL
  - CI_PROJECT_ID
  - CI_COMMIT_BRANCH
  - CI_COMMIT_SHORT_SHA
  - CI_PROJECT_PATH
  - CI_PIPELINE_URL
  - CI_JOB_URL

Optional env:
  - CI_BOT_FINGERPRINT            (must match the issue bot fingerprint; default: "clarissa-ci:tests:<branch>")
  - CI_BOT_RECOVERY_LABELS        (comma-separated; default: "ci,recovered")
  - CI_BOT_FLAKY_LABEL            (default: "ci-flaky-suspected")
  - CI_BOT_CLOSE_ON_RECOVERY      ("1" to close issue; default 0)
  - CI_BOT_MARK_FLAKY_ON_RECOVERY ("1" to add flaky label; default 0)
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
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
        "User-Agent": "clarissa-ci-recovery-bot/1.0",
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url=url, method=method, headers=headers, data=body)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return None
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} for {url}: {msg}") from e


def project_url(api: str, project_id: str, path: str) -> str:
    return f"{api}/projects/{urllib.parse.quote(project_id, safe='')}{path}"


def build_marker(fingerprint: str) -> str:
    return f"<!-- clarissa-ci-bot:{fingerprint} -->"


def find_existing_issue(api: str, project_id: str, token: str, marker: str) -> Optional[Dict[str, Any]]:
    q = urllib.parse.urlencode({"state": "opened", "search": marker, "per_page": 20})
    url = project_url(api, project_id, f"/issues?{q}")
    issues = api_request("GET", url, token) or []
    return issues[0] if isinstance(issues, list) and issues else None


def add_note(api: str, project_id: str, token: str, issue_iid: int, body: str) -> Any:
    url = project_url(api, project_id, f"/issues/{issue_iid}/notes")
    return api_request("POST", url, token, {"body": body})


def update_issue(api: str, project_id: str, token: str, issue_iid: int, labels: List[str], state_event: Optional[str]) -> Any:
    url = project_url(api, project_id, f"/issues/{issue_iid}")
    data: Dict[str, Any] = {}
    if labels:
        data["labels"] = ",".join(labels)
    if state_event:
        data["state_event"] = state_event
    return api_request("PUT", url, token, data)


def main() -> int:
    token = env("GITLAB_TOKEN")
    api = env("CI_API_V4_URL", "https://gitlab.com/api/v4")
    project_id = env("CI_PROJECT_ID")
    branch = env("CI_COMMIT_BRANCH", "unknown-branch")
    if not token or not project_id:
        print("Missing GITLAB_TOKEN or CI_PROJECT_ID", file=sys.stderr)
        return 2

    # Fingerprint must match the failure job's fingerprint. Default assumes tests job name.
    fingerprint = env("CI_BOT_FINGERPRINT", f"clarissa-ci:tests:{branch}")
    marker = build_marker(fingerprint)

    existing = find_existing_issue(api, project_id, token, marker)
    if not existing:
        print("No open deduped CI failure issue found; nothing to recover.")
        return 0

    iid = int(existing["iid"])
    project_path = env("CI_PROJECT_PATH", "unknown/project")
    short_sha = env("CI_COMMIT_SHORT_SHA", "unknown")
    pipeline_url = env("CI_PIPELINE_URL", "")
    job_url = env("CI_JOB_URL", "")

    recovery_labels = [s.strip() for s in env("CI_BOT_RECOVERY_LABELS", "ci,recovered").split(",") if s.strip()]
    mark_flaky = env("CI_BOT_MARK_FLAKY_ON_RECOVERY", "0").strip() == "1"
    flaky_label = env("CI_BOT_FLAKY_LABEL", "ci-flaky-suspected").strip()
    if mark_flaky and flaky_label:
        recovery_labels.append(flaky_label)

    close_on_recovery = env("CI_BOT_CLOSE_ON_RECOVERY", "0").strip() == "1"
    state_event = "close" if close_on_recovery else None

    note = (
        f"{marker}\n"
        f"✅ CI recovery detected for `{project_path}` on `{branch}` at `{short_sha}`.\n\n"
        f"- Pipeline: {pipeline_url}\n"
        f"- Job: {job_url}\n\n"
        f"{'Marked as flaky-suspected.' if mark_flaky else ''}\n"
        f"{'Issue closed automatically.' if close_on_recovery else ''}\n"
    )
    add_note(api, project_id, token, iid, note)
    update_issue(api, project_id, token, iid, recovery_labels, state_event)
    print(f"Updated issue !{iid} with recovery state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
