from swesmith.profiles.javascript import parse_log_jest, parse_log_vitest
from swebench.harness.constants import TestStatus


def test_parse_log_vitest_basic():
    log = """
✓ src/utils.test.ts (5 tests) 12ms
✓ src/core.test.ts (10 tests) 25ms
"""
    result = parse_log_vitest(log)
    assert len(result) == 2
    assert result["src/utils.test.ts"] == TestStatus.PASSED.value
    assert result["src/core.test.ts"] == TestStatus.PASSED.value


def test_parse_log_vitest_with_failures():
    log = """
✓ src/utils.test.ts (5 tests) 12ms
✗ src/core.test.ts (3 tests | 2 failed) 25ms
"""
    result = parse_log_vitest(log)
    passed_count = sum(1 for v in result.values() if v == TestStatus.PASSED.value)
    failed_count = sum(1 for v in result.values() if v == TestStatus.FAILED.value)
    assert passed_count == 1
    assert failed_count == 1


def test_parse_log_vitest_no_matches():
    log = """
Some random text
No test results here
"""
    result = parse_log_vitest(log)
    assert result == {}


def test_parse_log_jest_basic():
    log = """
  ✓ should add numbers (5ms)
  ✓ should subtract numbers (3ms)
  ✓ should multiply numbers (2ms)
"""
    result = parse_log_jest(log)
    assert len(result) == 3
    assert result["should add numbers"] == TestStatus.PASSED.value
    assert result["should subtract numbers"] == TestStatus.PASSED.value
    assert result["should multiply numbers"] == TestStatus.PASSED.value


def test_parse_log_jest_with_failures():
    log = """
  ✓ should add numbers (5ms)
  ✕ should subtract numbers (3ms)
  ✓ should multiply numbers (2ms)
"""
    result = parse_log_jest(log)
    passed_count = sum(1 for v in result.values() if v == TestStatus.PASSED.value)
    failed_count = sum(1 for v in result.values() if v == TestStatus.FAILED.value)
    assert passed_count == 2
    assert failed_count == 1


def test_parse_log_jest_with_skipped():
    log = """
  ✓ should add numbers (5ms)
  ○ should subtract numbers
  ✓ should multiply numbers (2ms)
"""
    result = parse_log_jest(log)
    passed_count = sum(1 for v in result.values() if v == TestStatus.PASSED.value)
    skipped_count = sum(1 for v in result.values() if v == TestStatus.SKIPPED.value)
    assert passed_count == 2
    assert skipped_count == 1


def test_parse_log_jest_no_matches():
    log = """
Some random text
No test results here
"""
    result = parse_log_jest(log)
    assert result == {}
