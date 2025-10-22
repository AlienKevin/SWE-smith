# Procedural Bug Generation Report for Instagram/MonkeyType

This report provides a comprehensive analysis of procedurally generated bugs for the Instagram/MonkeyType repository using the SWE-smith toolkit.

## Executive Summary

We successfully generated and validated **259 bugs** using 13 different procedural modification strategies. Of these, **222 bugs (85.7%)** passed validation by breaking at least one test, demonstrating the effectiveness of procedural bug generation for creating realistic software defects.

## Methodology

### Bug Generation Process

1. **Repository**: Instagram/MonkeyType (commit: 70c3acf6)
2. **Docker Image**: `jyangballin/swesmith.x86_64.instagram_1776_monkeytype.70c3acf6`
3. **Generation Strategy**: Procedural modifications using AST-based transformations
4. **Validation**: Docker-based test execution to verify bugs break existing tests

### Procedural Modifiers

The following 13 procedural modification strategies were applied:

1. **func_pm_remove_assign**: Remove variable assignments
2. **func_pm_remove_cond**: Remove conditional statements
3. **func_pm_remove_loop**: Remove loop constructs
4. **func_pm_op_swap**: Swap operands in binary operations
5. **func_pm_ctrl_shuffle**: Shuffle control flow statements
6. **func_pm_ctrl_invert_if**: Invert if-else conditions
7. **func_pm_op_change**: Change operators (e.g., + to -, < to >)
8. **func_pm_class_rm_funcs**: Remove functions from classes
9. **func_pm_class_shuffle_funcs**: Shuffle function order in classes
10. **func_pm_remove_wrapper**: Remove wrapper statements (try/with blocks)
11. **func_pm_class_rm_base**: Remove base classes from class definitions
12. **func_pm_op_change_const**: Change constant values in operations
13. **func_pm_op_break_chains**: Break chained operations

## Results

### Overall Statistics

| Metric | Value | Percentage |
|--------|-------|------------|
| Total bugs generated | 259 | 100% |
| Total bugs validated | 259 | 100% |
| Bugs that passed validation | 222 | 85.7% |
| Bugs that failed validation | 37 | 14.3% |
| Bugs that timed out | 1 | 0.4% |

### Per-Modifier Statistics

| Modifier | Generated | Validated | Passed | Pass Rate |
|----------|-----------|-----------|--------|-----------|
| func_pm_remove_assign | 70 | 70 | 64 | 91.4% |
| func_pm_remove_cond | 67 | 67 | 62 | 92.5% |
| func_pm_remove_loop | 24 | 24 | 22 | 91.7% |
| func_pm_op_swap | 15 | 15 | 9 | 60.0% |
| func_pm_ctrl_shuffle | 15 | 15 | 13 | 86.7% |
| func_pm_ctrl_invert_if | 14 | 14 | 14 | 100.0% |
| func_pm_op_change | 11 | 11 | 11 | 100.0% |
| func_pm_class_rm_funcs | 11 | 11 | 8 | 72.7% |
| func_pm_class_shuffle_funcs | 11 | 11 | 0 | 0.0% |
| func_pm_remove_wrapper | 7 | 7 | 6 | 85.7% |
| func_pm_class_rm_base | 7 | 7 | 7 | 100.0% |
| func_pm_op_change_const | 4 | 4 | 3 | 75.0% |
| func_pm_op_break_chains | 3 | 3 | 3 | 100.0% |

### Test Failure Statistics

| Modifier | Avg F2P | Min F2P | Max F2P | Avg P2P |
|----------|---------|---------|---------|---------|
| func_pm_remove_assign | 13.60 | 0 | 71 | 339.59 |
| func_pm_remove_cond | 8.99 | 0 | 115 | 354.51 |
| func_pm_remove_loop | 6.17 | 0 | 22 | 362.83 |
| func_pm_op_swap | 6.20 | 0 | 51 | 362.80 |
| func_pm_ctrl_shuffle | 7.80 | 0 | 17 | 361.20 |
| func_pm_ctrl_invert_if | 17.71 | 2 | 100 | 351.29 |
| func_pm_op_change | 14.00 | 1 | 126 | 355.00 |
| func_pm_class_rm_funcs | 11.73 | 0 | 49 | 323.73 |
| func_pm_class_shuffle_funcs | 0.00 | 0 | 0 | 369.00 |
| func_pm_remove_wrapper | 14.57 | 0 | 52 | 354.43 |
| func_pm_class_rm_base | 12.29 | 3 | 49 | 356.71 |
| func_pm_op_change_const | 2.25 | 0 | 5 | 366.75 |
| func_pm_op_break_chains | 3.67 | 3 | 4 | 365.33 |

**Legend:**
- **F2P (Fail-to-Pass)**: Number of tests that fail before applying the patch and pass after applying it (indicates bug severity)
- **P2P (Pass-to-Pass)**: Number of tests that pass both before and after applying the patch (indicates non-regression)

### Distribution Summary

| Metric | Value |
|--------|-------|
| Average tests broken per bug (F2P) | 10.24 |
| Median tests broken per bug (F2P) | 5 |
| Min tests broken per bug (F2P) | 0 |
| Max tests broken per bug (F2P) | 126 |
| Average tests maintained per bug (P2P) | 351.64 |
| Median tests maintained per bug (P2P) | 364 |

## Key Findings

### Most Effective Modifiers (100% Pass Rate)

The following modifiers achieved a 100% validation pass rate, meaning every bug they generated broke at least one test:

1. **func_pm_ctrl_invert_if** (14 bugs): Inverting if-else conditions is highly effective, with an average of 17.71 tests broken per bug (highest average).
2. **func_pm_op_change** (11 bugs): Changing operators consistently produces bugs that break tests, with an average of 14.00 tests broken.
3. **func_pm_class_rm_base** (7 bugs): Removing base classes from class definitions is very effective, breaking an average of 12.29 tests.
4. **func_pm_op_break_chains** (3 bugs): Breaking chained operations is reliable but generates fewer bugs due to fewer applicable candidates.
5. **func_pm_op_change_const** (3 bugs): Changing constant values is effective but has a lower average F2P (2.25).

### High-Volume Effective Modifiers

These modifiers generated the most bugs while maintaining high pass rates:

1. **func_pm_remove_assign** (70 bugs, 91.4% pass rate): Removing variable assignments is the most prolific modifier, generating 70 bugs with 64 passing validation. Average F2P: 13.60.
2. **func_pm_remove_cond** (67 bugs, 92.5% pass rate): Removing conditional statements is highly effective, with 62 bugs passing validation. Average F2P: 8.99.
3. **func_pm_remove_loop** (24 bugs, 91.7% pass rate): Removing loop constructs is consistently effective. Average F2P: 6.17.

### Least Effective Modifier

**func_pm_class_shuffle_funcs** (11 bugs, 0% pass rate): Shuffling function order within classes did not break any tests. This suggests that function order in classes is not semantically significant in the MonkeyType codebase, or the test suite does not depend on function ordering.

### Moderate Effectiveness

**func_pm_op_swap** (15 bugs, 60% pass rate): Swapping operands in binary operations has moderate effectiveness, with only 9 out of 15 bugs passing validation. This suggests that many operations in the codebase are commutative or the test suite doesn't catch all operand swap errors.

## Insights

### Bug Severity Distribution

The distribution of F2P counts shows that most bugs break a moderate number of tests:
- **Median**: 5 tests broken per bug
- **Average**: 10.24 tests broken per bug
- **Range**: 0 to 126 tests broken

This indicates that procedural modifications create bugs with varying severity levels, from minor issues affecting a few tests to critical bugs affecting over 100 tests.

### Test Suite Coverage

The high average P2P count (351.64 tests maintained per bug) indicates that:
1. The MonkeyType test suite is comprehensive, with approximately 369 total tests.
2. Most bugs are localized, affecting specific functionality without breaking the entire test suite.
3. The test suite has good isolation between test cases.

### Modifier Applicability

The number of bugs generated per modifier varies significantly:
- **High applicability**: func_pm_remove_assign (70), func_pm_remove_cond (67)
- **Medium applicability**: func_pm_remove_loop (24), func_pm_ctrl_invert_if (14)
- **Low applicability**: func_pm_op_break_chains (3), func_pm_op_change_const (4)

This variation reflects the code patterns present in the MonkeyType codebase. For example, the high number of assignment removals suggests the codebase has many variable assignments, while the low number of chained operations suggests fewer method chains.

## Recommendations

### For Bug Generation

1. **Prioritize high-pass-rate modifiers**: Focus on modifiers with 100% pass rates (ctrl_invert_if, op_change, class_rm_base) for generating high-quality bugs.
2. **Leverage high-volume modifiers**: Use remove_assign and remove_cond for generating large datasets of bugs.
3. **Investigate class_shuffle_funcs**: This modifier's 0% pass rate suggests it may need refinement or may not be applicable to Python codebases where function order doesn't matter.
4. **Combine modifiers**: Consider combining multiple modifications to create more complex, realistic bugs.

### For Test Suite Improvement

1. **Operand swap testing**: The 60% pass rate for op_swap suggests the test suite could benefit from more tests that verify operand order matters.
2. **Function ordering**: If function order is semantically significant, add tests to verify correct ordering.

### For Future Work

1. **Cross-repository analysis**: Apply these modifiers to other repositories to identify which strategies are universally effective vs. repository-specific.
2. **Modifier refinement**: Investigate why certain modifiers have lower pass rates and refine them to generate more realistic bugs.
3. **Severity prediction**: Develop models to predict bug severity (F2P count) based on modifier type and code context.

## Conclusion

Procedural bug generation for Instagram/MonkeyType successfully created 222 validated bugs (85.7% success rate) using 13 different modification strategies. The most effective strategies include inverting if-else conditions, changing operators, and removing base classes, all achieving 100% validation pass rates. High-volume strategies like removing assignments and conditionals generated the most bugs while maintaining over 90% pass rates.

The analysis reveals that procedural bug generation is a viable approach for creating realistic software defects at scale, with different modifiers exhibiting varying effectiveness based on code patterns and test suite characteristics. These findings can inform future bug generation efforts and help improve both bug generation strategies and test suite quality.

## Appendix: Scripts

### procedural_bug_gen.sh

A bash script that automates the entire procedural bug generation pipeline:
1. Verifies Docker image availability
2. Generates bugs using procedural modifications
3. Collects patches into a single JSON file
4. Runs validation to filter bugs that break tests

Usage: `./scripts/procedural_bug_gen.sh [repo_name] [max_bugs]`

### analyze_bugs.py

A Python script that analyzes bug generation and validation results:
1. Collects statistics on generated and validated bugs
2. Breaks down results by modifier type
3. Calculates pass rates and test failure statistics
4. Generates detailed reports in both console and JSON formats

Usage: `python scripts/analyze_bugs.py <repo_id>`

## Files Generated

- `logs/bug_gen/Instagram__MonkeyType.70c3acf6/`: Directory containing all generated bug patches and metadata
- `logs/bug_gen/Instagram__MonkeyType.70c3acf6_all_patches.json`: Consolidated JSON file with all patches
- `logs/run_validation/Instagram__MonkeyType.70c3acf6/`: Directory containing validation results for each bug
- `logs/analysis/Instagram__MonkeyType.70c3acf6_analysis.json`: Detailed JSON analysis report

---

**Report Generated**: 2025-10-22  
**Repository**: Instagram/MonkeyType (commit: 70c3acf6)  
**Total Bugs Generated**: 259  
**Total Bugs Validated**: 222 (85.7%)
