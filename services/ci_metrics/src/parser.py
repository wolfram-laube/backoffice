"""JUnit XML parser for extracting test metrics."""

import xml.etree.ElementTree as ET
from .models import TestCase, TestSuiteResult


def parse_junit_xml(xml_content: str) -> list[TestSuiteResult]:
    """Parse JUnit XML content into structured test results.

    Handles both single <testsuite> and <testsuites> wrapper formats.
    """
    root = ET.fromstring(xml_content)
    suites = []

    # Handle both <testsuites><testsuite>... and standalone <testsuite>
    if root.tag == "testsuites":
        suite_elements = root.findall("testsuite")
    elif root.tag == "testsuite":
        suite_elements = [root]
    else:
        return suites

    for suite_el in suite_elements:
        test_cases = []

        for tc_el in suite_el.findall("testcase"):
            # Determine status
            if tc_el.find("failure") is not None:
                status = "failed"
                msg = tc_el.find("failure").get("message", "")
            elif tc_el.find("error") is not None:
                status = "error"
                msg = tc_el.find("error").get("message", "")
            elif tc_el.find("skipped") is not None:
                status = "skipped"
                msg = tc_el.find("skipped").get("message", "")
            else:
                status = "passed"
                msg = None

            test_cases.append(TestCase(
                name=tc_el.get("name", "unknown"),
                classname=tc_el.get("classname", ""),
                status=status,
                duration_s=float(tc_el.get("time", 0)),
                message=msg,
            ))

        # Counts from attributes (more reliable) or derive from test cases
        tests = int(suite_el.get("tests", len(test_cases)))
        failures = int(suite_el.get("failures", 0))
        errors = int(suite_el.get("errors", 0))
        skipped = int(suite_el.get("skipped", 0))
        passed = tests - failures - errors - skipped

        suites.append(TestSuiteResult(
            suite_name=suite_el.get("name", "unknown"),
            tests=tests,
            passed=passed,
            failed=failures,
            skipped=skipped,
            errors=errors,
            duration_s=float(suite_el.get("time", 0)),
            test_cases=test_cases,
        ))

    return suites
