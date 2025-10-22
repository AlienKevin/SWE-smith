# Rust Procedural Bug Generation Analysis Report

## Executive Summary

This report presents a comprehensive analysis of procedural bug generation effectiveness for Rust repositories using the 10 Rust procedural modifiers introduced in PR #2. The analysis was conducted across all 19 Rust profiles in the SWE-smith repository.

**Key Results:**
- **Total Rust Profiles Tested**: 19/19 (100% coverage)
- **Total Bugs Generated**: 610 bugs
- **Average Bugs per Profile**: 32.1 bugs
- **Modifier Range**: 4-90 bugs per profile

## Quick Links

- **Testing Scripts**: `scripts/test_rust_local.py`, `scripts/test_rust_procedural.sh`
- **Analysis Scripts**: `scripts/analyze_rust_generation_only.py`, `scripts/analyze_rust_comprehensive.py`
- **Related PRs**: [PR #2](https://github.com/AlienKevin/SWE-smith/pull/2) (Rust modifiers), [PR #3](https://github.com/AlienKevin/SWE-smith/pull/3) (Testing procedure)

## Results Summary

### Per-Modifier Effectiveness

| Modifier | Total Generated | Profiles Used | Avg per Profile | % of Total |
|----------|-----------------|---------------|-----------------|------------|
| `func_pm_ctrl_shuffle` | 168 | 16 | 10.5 | 27.5% |
| `func_pm_ctrl_invert_if` | 79 | 17 | 4.6 | 13.0% |
| `func_pm_remove_assign` | 73 | 17 | 4.3 | 12.0% |
| `func_pm_flip_operators` | 68 | 17 | 4.0 | 11.1% |
| `func_pm_op_swap` | 68 | 17 | 4.0 | 11.1% |
| `func_pm_op_change` | 63 | 16 | 3.9 | 10.3% |
| `func_pm_remove_cond` | 30 | 12 | 2.5 | 4.9% |
| `func_pm_op_change_const` | 29 | 10 | 2.9 | 4.8% |
| `func_pm_remove_loop` | 21 | 11 | 1.9 | 3.4% |
| `func_pm_op_break_chains` | 11 | 8 | 1.4 | 1.8% |

**Key Findings:**
- **Most Prolific**: `func_pm_ctrl_shuffle` generated 168 bugs (27.5% of total)
- **Most Consistent**: `func_pm_remove_assign` and `func_pm_ctrl_invert_if` used in 17/19 profiles (89.5%)
- **Control Flow Dominance**: Control flow modifiers generated 247 bugs (40.5% of total)

### Top 5 Profiles by Bug Count

1. **orium/rpds**: 90 bugs (func_pm_ctrl_shuffle: 75)
2. **dtolnay/semver**: 67 bugs (func_pm_flip_operators: 14)
3. **rayon-rs/rayon**: 51 bugs (func_pm_op_swap: 11)
4. **BurntSushi/rust-csv**: 50 bugs (func_pm_ctrl_shuffle: 9)
5. **marshallpierce/rust-base64**: 44 bugs (func_pm_op_change: 10)

## Commands Used

```bash
# Generate bugs for all Rust profiles
uv run python scripts/test_rust_local.py --max-bugs 100

# Analyze generation results
uv run python scripts/analyze_rust_generation_only.py

# View detailed results (after running analysis)
cat logs/analysis/rust_generation_only.json
cat logs/analysis/rust_generation_only.md
```

## Limitations

⚠️ **Important**: This analysis only covers the bug generation phase. Validation testing requires Docker images which were not available.

**Missing Metrics:**
- Validation pass rate (% of bugs that actually break tests)
- F2P (fail-to-pass) test counts per bug
- P2P (pass-to-pass) test counts per bug
- Semantic correctness of generated bugs

## Next Steps

To complete the full testing procedure:

1. **Build Docker Images** (required for validation)
2. **Run Validation**: `python -m swesmith.harness.valid logs/bug_gen/<repo_id>_all_patches.json`
3. **Analyze Validation Results**: `python scripts/analyze_bugs.py <repo_id>`
4. **Generate Comprehensive Report**: `python scripts/analyze_rust_comprehensive.py`

## Methodology

### Bug Generation Process

1. Clone each Rust repository at the specified commit
2. Extract up to 100 code entities (functions) per repository
3. Apply each of the 10 Rust procedural modifiers to applicable entities
4. Generate diffs and metadata for each successful modification

### Rust Procedural Modifiers

**Control Flow (2 modifiers):**
- `func_pm_ctrl_invert_if`: Inverts if-else conditions or swaps their bodies
- `func_pm_ctrl_shuffle`: Shuffles lines within a function body

**Operations (5 modifiers):**
- `func_pm_op_change`: Changes operators (e.g., `==` to `!=`, `+` to `-`)
- `func_pm_op_swap`: Swaps operands in binary operations
- `func_pm_flip_operators`: Flips comparison operators (e.g., `<` to `>`)
- `func_pm_break_chains`: Breaks chained operations
- `func_pm_op_change_const`: Changes constant values in expressions

**Remove (3 modifiers):**
- `func_pm_remove_assign`: Removes assignment statements
- `func_pm_remove_cond`: Removes conditional statements
- `func_pm_remove_loop`: Removes loop statements

## Detailed Results

See the full report with per-profile breakdowns, distribution statistics, and recommendations in the complete analysis document.

---

**Report Generated**: 2025-10-22  
**Session**: https://app.devin.ai/sessions/eb3d9417d5cc475ca78f145d9ea3b30a  
**Requested by**: Kevin Li (@AlienKevin)
