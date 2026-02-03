#!/usr/bin/env python3
"""Generate a standalone MR report Markdown artifact.

This report mirrors the unified MR note content but is stored as a file artifact for export.
It composes:
- status overview table (snapshots/contracts/governance)
- snapshot diff summary (tests/golden/summary.md)
- contract summary (tests/contracts/summary.md)
- governance impact (tests/governance/impact.md)
- links (pipeline/job/mr)

Output:
- reports/mr_report.md
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

def env(name: str, default: str = "") -> str:
    return os.getenv(name, default) or default

def read_if_exists(path: str) -> str:
    p = Path(path)
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return ""

def status_row(label: str, ok: Optional[bool]) -> str:
    if ok is None:
        return f"| {label} | ⚪ n/a |"
    return f"| {label} | {'✅ pass' if ok else '❌ fail'} |"

def main() -> int:
    snapshot = read_if_exists(env("CI_BOT_SNAPSHOT_SUMMARY_PATH", "tests/golden/summary.md"))
    contract = read_if_exists(env("CI_BOT_CONTRACT_SUMMARY_PATH", "tests/contracts/summary.md"))
    gov = read_if_exists(env("CI_BOT_GOVERNANCE_IMPACT_PATH", "tests/governance/impact.md"))

    snapshot_ok = (snapshot == "")
    contract_ok = (contract == "")
    gov_hit = (gov != "")

    pipeline_url = env("CI_PIPELINE_URL")
    job_url = env("CI_JOB_URL")
    mr_url = env("CI_MERGE_REQUEST_PROJECT_URL")  # may be absent
    project = env("CI_PROJECT_PATH")
    sha = env("CI_COMMIT_SHORT_SHA")
    branch = env("CI_COMMIT_REF_NAME")

    lines = []
    lines.append("# CLARISSA CI/MR Report")
    lines.append("")
    if project or sha or branch:
        lines.append("## Context")
        lines.append("")
        if project: lines.append(f"- Project: `{project}`")
        if branch: lines.append(f"- Ref: `{branch}`")
        if sha: lines.append(f"- Commit: `{sha}`")
        lines.append("")

    lines.append("## 🧭 CI status overview")
    lines.append("")
    lines.append("| Check | Status |")
    lines.append("|---|---|")
    lines.append(status_row("CLI snapshots", snapshot_ok))
    lines.append(status_row("Contract tests", contract_ok))
    lines.append(status_row("Governance impact", None if not gov_hit else False))
    lines.append("")

    if snapshot:
        lines.append("---")
        lines.append("")
        lines.append("## 🧾 Snapshot diff summary")
        lines.append("")
        lines.append(snapshot)
        lines.append("")

    if contract:
        lines.append("---")
        lines.append("")
        lines.append("## 🔒 Contract status")
        lines.append("")
        lines.append(contract)
        lines.append("")

    if gov:
        lines.append("---")
        lines.append("")
        lines.append("## 🛂 Governance impact")
        lines.append("")
        lines.append(gov)
        lines.append("")

    links = []
    if pipeline_url: links.append(f"- 🔗 Pipeline: {pipeline_url}")
    if job_url: links.append(f"- 🧩 Job: {job_url}")
    if mr_url: links.append(f"- 📝 MR: {mr_url}")
    if links:
        lines.append("---")
        lines.append("")
        lines.append("## 🔗 Links")
        lines.append("")
        lines.extend(links)
        lines.append("")

    out_dir = Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "mr_report.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
