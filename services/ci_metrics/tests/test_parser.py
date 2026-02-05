"""Tests for JUnit XML parser."""

import pytest
from src.parser import parse_junit_xml


SAMPLE_JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="1" skipped="1" tests="5" time="0.642">
    <testcase classname="tests.test_unit" name="test_add" time="0.001"/>
    <testcase classname="tests.test_unit" name="test_subtract" time="0.002"/>
    <testcase classname="tests.test_unit" name="test_multiply" time="0.001"/>
    <testcase classname="tests.test_unit" name="test_divide_zero" time="0.003">
      <failure message="ZeroDivisionError">Traceback...</failure>
    </testcase>
    <testcase classname="tests.test_unit" name="test_slow" time="0.100">
      <skipped message="slow test"/>
    </testcase>
  </testsuite>
</testsuites>"""

SINGLE_SUITE = """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="single" errors="0" failures="0" skipped="0" tests="2" time="0.100">
  <testcase classname="tests.smoke" name="test_health" time="0.010"/>
  <testcase classname="tests.smoke" name="test_version" time="0.005"/>
</testsuite>"""


class TestJUnitParser:
    """Test JUnit XML parsing."""

    def test_parse_testsuites_wrapper(self):
        suites = parse_junit_xml(SAMPLE_JUNIT)
        assert len(suites) == 1

    def test_suite_counts(self):
        suite = parse_junit_xml(SAMPLE_JUNIT)[0]
        assert suite.tests == 5
        assert suite.passed == 3
        assert suite.failed == 1
        assert suite.skipped == 1
        assert suite.errors == 0

    def test_suite_duration(self):
        suite = parse_junit_xml(SAMPLE_JUNIT)[0]
        assert suite.duration_s == pytest.approx(0.642)

    def test_suite_name(self):
        suite = parse_junit_xml(SAMPLE_JUNIT)[0]
        assert suite.suite_name == "pytest"

    def test_test_cases_count(self):
        suite = parse_junit_xml(SAMPLE_JUNIT)[0]
        assert len(suite.test_cases) == 5

    def test_passed_case(self):
        tc = parse_junit_xml(SAMPLE_JUNIT)[0].test_cases[0]
        assert tc.name == "test_add"
        assert tc.status == "passed"
        assert tc.classname == "tests.test_unit"

    def test_failed_case(self):
        tc = parse_junit_xml(SAMPLE_JUNIT)[0].test_cases[3]
        assert tc.name == "test_divide_zero"
        assert tc.status == "failed"
        assert tc.message == "ZeroDivisionError"

    def test_skipped_case(self):
        tc = parse_junit_xml(SAMPLE_JUNIT)[0].test_cases[4]
        assert tc.name == "test_slow"
        assert tc.status == "skipped"

    def test_single_suite_format(self):
        suites = parse_junit_xml(SINGLE_SUITE)
        assert len(suites) == 1
        assert suites[0].tests == 2
        assert suites[0].passed == 2
        assert suites[0].suite_name == "single"

    def test_empty_xml(self):
        suites = parse_junit_xml("<root/>")
        assert len(suites) == 0

    def test_case_durations(self):
        cases = parse_junit_xml(SAMPLE_JUNIT)[0].test_cases
        assert cases[0].duration_s == pytest.approx(0.001)
        assert cases[4].duration_s == pytest.approx(0.100)
