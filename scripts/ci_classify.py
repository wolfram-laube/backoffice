#!/usr/bin/env python3
"""
CI classification script

Writes ci_classify.env (dotenv) with:
- CI_BOT_CONFIRMED_FAILURE=1/0
- CI_BOT_FLAKY=1/0
- CI_BOT_FAILURES_SAMPLE="...optional..."

Logic:
- If junit.xml has failures and rerun_exit_code.txt exists:
    - rerun exit code == 0 => flaky (not confirmed)
    - rerun exit code != 0 => confirmed failure
- If junit.xml has failures and no rerun info => confirmed failure
- If junit.xml has no failures => no failure

This job runs regardless of pipeline status and is used to gate automation.
"""

from __future__ import annotations
import os
import sys
import xml.etree.ElementTree as ET

def junit_has_failures(path: str) -> bool:
    if not os.path.exists(path):
        return False
    try:
        root = ET.parse(path).getroot()
    except Exception:
        return False
    # JUnit: testsuite may have failures/errors attrs, but robustly scan nodes
    for tc in root.findall(".//testcase"):
        if tc.find("failure") is not None or tc.find("error") is not None:
            return True
    return False

def main() -> int:
    failed_first = junit_has_failures("junit.xml")
    rerun_code = None
    if os.path.exists("rerun_exit_code.txt"):
        try:
            rerun_code = int(open("rerun_exit_code.txt","r").read().strip())
        except Exception:
            rerun_code = None

    confirmed = 0
    flaky = 0
    if failed_first:
        if rerun_code is None:
            confirmed = 1
        elif rerun_code == 0:
            confirmed = 0
            flaky = 1
        else:
            confirmed = 1
    else:
        confirmed = 0
        flaky = 0

    with open("ci_classify.env", "w", encoding="utf-8") as f:
        f.write(f"CI_BOT_CONFIRMED_FAILURE={confirmed}\n")
        f.write(f"CI_BOT_FLAKY={flaky}\n")
    print(f"Classify: failed_first={failed_first} rerun_code={rerun_code} confirmed={confirmed} flaky={flaky}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
