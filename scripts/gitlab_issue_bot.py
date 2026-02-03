#!/usr/bin/env python3
"""
GitLab CI Issue Bot (stdlib only) — refined

Features:
- Create or update a GitLab issue on CI failures with deduping
- Optional "silent until N consecutive failures on main" behavior
- Optional assignee rotation (deterministic) using pipeline ID
- Optional label updates and issue closure support via companion script

Required env (GitLab CI provides most automatically):
  - GITLAB_TOKEN
  - CI_API_V4_URL
  - CI_PROJECT_ID
  - CI_PIPELINE_URL
  - CI_JOB_URL
  - CI_COMMIT_BRANCH
  - CI_COMMIT_SHORT_SHA
  - CI_PROJECT_PATH
  - CI_PIPELINE_ID

Optional env:
  - CI_BOT_FINGERPRINT                 (dedupe key; default: "clarissa-ci:<job>:<branch>")
  - CI_BOT_TITLE                       (issue title template)
  - CI_BOT_LABELS                      (comma-separated labels, default: "ci,ci-failure")
  - CI_BOT_ASSIGNEE_IDS                (comma-separated numeric GitLab user IDs)
  - CI_BOT_ASSIGNEE_ROTATION_IDS       (comma-separated numeric IDs used if CI_BOT_ASSIGNEE_IDS empty)
  - CI_BOT_CREATE_AFTER_N_FAILURES     (int; default 1; only create after N consecutive failed pipelines on ref)
  - CI_BOT_SILENT_MODE                 ("1" to avoid creating new issues; will only comment if issue exists)
  - CI_BOT_MAX_TESTS                   (max failing tests to include; default 10)
  - CI_BOT_JUNIT_PATH                  (default "junit.xml")
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
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
        "User-Agent": "clarissa-ci-issue-bot/1.1",
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


def parse_junit_failures(path: str, max_tests: int) -> List[str]:
    if not os.path.exists(path):
        return []
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except Exception:
        return []

    failures: List[str] = []
    for tc in root.findall(".//testcase"):
        if len(failures) >= max_tests:
            break
        failed = tc.find("failure") is not None or tc.find("error") is not None
        if failed:
            classname = (tc.attrib.get("classname") or "").strip()
            name = (tc.attrib.get("name") or "").strip()
            failures.append(f"{classname}::{name}" if classname and name else (name or classname or "unknown_test"))
    return failures


def build_marker(fingerprint: str) -> str:
    return f"<!-- clarissa-ci-bot:{fingerprint} -->"


def project_url(api: str, project_id: str, path: str) -> str:
    return f"{api}/projects/{urllib.parse.quote(project_id, safe='')}{path}"


def get_consecutive_failed_pipelines(api: str, project_id: str, token: str, ref: str, limit: int) -> int:
    """
    Counts consecutive pipelines on a ref starting from the most recent,
    stopping at the first non-failed (success/canceled/skipped/running) pipeline.
    """
    if limit <= 1:
        return 1
    q = urllib.parse.urlencode({"ref": ref, "per_page": str(min(limit, 50))})
    url = project_url(api, project_id, f"/pipelines?{q}")
    pipelines = api_request("GET", url, token) or []
    count = 0
    for p in pipelines:
        status = (p.get("status") or "").lower()
        if status == "failed":
            count += 1
            if count >= limit:
                break
        else:
            break
    return count


def find_existing_issue(api: str, project_id: str, token: str, marker: str) -> Optional[Dict[str, Any]]:
    q = urllib.parse.urlencode({"state": "opened", "search": marker, "per_page": 20})
    url = project_url(api, project_id, f"/issues?{q}")
    issues = api_request("GET", url, token) or []
    return issues[0] if isinstance(issues, list) and issues else None


def create_issue(api: str, project_id: str, token: str, title: str, description: str,
                 labels: List[str], assignee_ids: List[int]) -> Dict[str, Any]:
    url = project_url(api, project_id, "/issues")
    data: Dict[str, Any] = {"title": title, "description": description}
    if labels:
        data["labels"] = ",".join(labels)
    if assignee_ids:
        data["assignee_ids"] = assignee_ids
    return api_request("POST", url, token, data)


def add_note(api: str, project_id: str, token: str, issue_iid: int, body: str) -> Any:
    url = project_url(api, project_id, f"/issues/{issue_iid}/notes")
    return api_request("POST", url, token, {"body": body})


def choose_assignee(rotation_ids: List[int], pipeline_id: str) -> List[int]:
    if not rotation_ids:
        return []
    try:
        pid = int(pipeline_id)
    except Exception:
        pid = sum(ord(c) for c in pipeline_id) if pipeline_id else 0
    return [rotation_ids[pid % len(rotation_ids)]]


def main() -> int:
    token = env("GITLAB_TOKEN")
    api = env("CI_API_V4_URL", "https://gitlab.com/api/v4")
    project_id = env("CI_PROJECT_ID")
    if not token or not project_id:
        print("Missing GITLAB_TOKEN or CI_PROJECT_ID", file=sys.stderr)
        return 2

    ref = env("CI_COMMIT_BRANCH", "unknown-branch")
    job = env("CI_JOB_NAME", "tests")
    pipeline_id = env("CI_PIPELINE_ID", "")
    short_sha = env("CI_COMMIT_SHORT_SHA", "unknown")
    project_path = env("CI_PROJECT_PATH", "unknown/project")
    pipeline_url = env("CI_PIPELINE_URL", "")
    job_url = env("CI_JOB_URL", "")


    # Gate: only proceed if failure is confirmed (after rerun classification)
    confirmed = env("CI_BOT_CONFIRMED_FAILURE", "1").strip() == "1"
    flaky = env("CI_BOT_FLAKY", "0").strip() == "1"
    if not confirmed:
        if flaky:
            print("CI failure classified as flaky (rerun passed); skipping issue creation/update.")
        else:
            print("CI failure not confirmed; skipping issue creation/update.")
        return 0

    fingerprint = env("CI_BOT_FINGERPRINT", f"clarissa-ci:{job}:{ref}")
    marker = build_marker(fingerprint)

    silent_mode = env("CI_BOT_SILENT_MODE", "0").strip() == "1"

    create_after = int(env("CI_BOT_CREATE_AFTER_N_FAILURES", "1") or "1")
    # Only gate creation when no existing issue
    consecutive_failed = get_consecutive_failed_pipelines(api, project_id, token, ref, create_after) if create_after > 1 else create_after

    labels = [s.strip() for s in env("CI_BOT_LABELS", "ci,ci-failure,ci-regression-confirmed").split(",") if s.strip()]

    assignee_ids: List[int] = []
    assignee_raw = env("CI_BOT_ASSIGNEE_IDS", "").strip()
    if assignee_raw:
        for part in assignee_raw.split(","):
            part = part.strip()
            if part.isdigit():
                assignee_ids.append(int(part))

    if not assignee_ids:
        rotation_raw = env("CI_BOT_ASSIGNEE_ROTATION_IDS", "").strip()
        rotation_ids = [int(x.strip()) for x in rotation_raw.split(",") if x.strip().isdigit()]
        assignee_ids = choose_assignee(rotation_ids, pipeline_id)

    max_tests = int(env("CI_BOT_MAX_TESTS", "10") or "10")
    junit_path = env("CI_BOT_JUNIT_PATH", "junit.xml")
    failures = parse_junit_failures(junit_path, max_tests=max_tests)

    title_tpl = env("CI_BOT_TITLE", "CI failure: {project}@{sha} ({branch})")
    title = title_tpl.format(project=project_path, sha=short_sha, branch=ref)

    failures_md = ""
    if failures:
        failures_md = "\n\n**Failing tests (sample):**\n" + "\n".join([f"- `{t}`" for t in failures])

    description = (
        f"{marker}\n"
        f"CI detected a failure.\n\n"
        f"- Project: `{project_path}`\n"
        f"- Branch: `{ref}`\n"
        f"- Commit: `{short_sha}`\n"
        f"- Pipeline: {pipeline_url}\n"
        f"- Job: {job_url}\n"
        f"{failures_md}\n\n"
        f"**Signal gating**\n"
        f"- Create-after-N failures: `{create_after}` (observed consecutive failed pipelines: `{consecutive_failed}`)\n\n"
        f"**Next steps**\n"
        f"- Re-run the job to check flakiness.\n"
        f"- If reproducible, tag as regression and link root-cause.\n"
    )

    existing = find_existing_issue(api, project_id, token, marker)

    note = (
        f"{marker}\n"
        f"New failure observed for `{project_path}` on `{ref}` at `{short_sha}`.\n\n"
        f"- Pipeline: {pipeline_url}\n"
        f"- Job: {job_url}\n"
        f"{failures_md}\n"
    )

    if existing:
        iid = int(existing["iid"])
        add_note(api, project_id, token, iid, note)
        print(f"Updated existing issue !{iid} {existing.get('web_url','')}")
        return 0

    if silent_mode:
        print("Silent mode enabled and no existing issue found; skipping issue creation.")
        return 0

    if create_after > 1 and consecutive_failed < create_after:
        print(f"Create-after gate not met: need {create_after}, observed {consecutive_failed}. Skipping issue creation.")
        return 0

    created = create_issue(api, project_id, token, title, description, labels, assignee_ids)
    print(f"Created issue !{created.get('iid')} {created.get('web_url','')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
