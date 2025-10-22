#!/usr/bin/env python3
"""
Comprehensive analysis of Rust procedural bug generation across all profiles.

This script aggregates results from all Rust repositories and provides:
- Overall statistics across all Rust profiles
- Per-profile breakdown
- Per-modifier effectiveness analysis
- Comparative analysis of procedural modification methods

Usage:
    python scripts/analyze_rust_comprehensive.py [--output OUTPUT_FILE]
"""

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

from swebench.harness.constants import FAIL_TO_PASS, LOG_REPORT, PASS_TO_PASS


RUST_PROFILES = [
    "dtolnay__anyhow.1d7ef1db",
    "marshallpierce__rust-base64.cac5ff84",
    "clap-rs__clap.3716f9f4",
    "hyperium__hyper.c88df788",
    "rust-itertools__itertools.041c733c",
    "serde-rs__json.cd55b5a0",
    "rust-lang__log.3aa1359e",
    "dtolnay__semver.37bcbe69",
    "tokio-rs__tokio.ab3ff69c",
    "uuid-rs__uuid.2fd9b614",
    "rust-lang__mdBook.37273ba8",
    "BurntSushi__rust-csv.da000888",
    "servo__html5ever.b93afc94",
    "BurntSushi__byteorder.5a82625f",
    "chronotope__chrono.d43108cb",
    "orium__rpds.3e7c8ae6",
    "rayon-rs__rayon.1fd20485",
    "BurntSushi__ripgrep.3b7fd442",
    "rust-lang__rust-clippy.f4f579f4",
]


def extract_modifier_name(instance_id: str) -> str:
    """Extract the modifier name from an instance ID."""
    parts = instance_id.split(".")
    if len(parts) >= 3:
        last_part = parts[-1]
        if "__" in last_part:
            return last_part.split("__")[0]
    return "unknown"


def analyze_single_profile(repo_id: str) -> Dict[str, Any]:
    """Analyze bugs for a single repository profile."""
    bug_gen_dir = Path("logs/bug_gen") / repo_id
    validation_dir = Path("logs/run_validation") / repo_id

    result = {
        "repo_id": repo_id,
        "exists": False,
        "total_generated": 0,
        "total_validated": 0,
        "total_passed": 0,
        "total_failed": 0,
        "by_modifier": defaultdict(
            lambda: {
                "generated": 0,
                "validated": 0,
                "passed": 0,
                "failed": 0,
                "f2p_counts": [],
                "p2p_counts": [],
            }
        ),
    }

    if not bug_gen_dir.exists():
        return result

    result["exists"] = True

    for root, _, files in os.walk(bug_gen_dir):
        for file in files:
            if file.startswith("bug__") and file.endswith(".diff"):
                result["total_generated"] += 1
                modifier_name = file.split("bug__")[1].split("__")[0]
                result["by_modifier"][modifier_name]["generated"] += 1

    if validation_dir.exists():
        for instance_dir in os.listdir(validation_dir):
            instance_path = validation_dir / instance_dir
            report_path = instance_path / LOG_REPORT

            if report_path.exists():
                with open(report_path, "r") as f:
                    report = json.load(f)

                modifier_name = extract_modifier_name(instance_dir)
                result["total_validated"] += 1
                result["by_modifier"][modifier_name]["validated"] += 1

                f2p_count = len(report.get(FAIL_TO_PASS, []))
                p2p_count = len(report.get(PASS_TO_PASS, []))

                result["by_modifier"][modifier_name]["f2p_counts"].append(f2p_count)
                result["by_modifier"][modifier_name]["p2p_counts"].append(p2p_count)

                if f2p_count > 0:
                    result["total_passed"] += 1
                    result["by_modifier"][modifier_name]["passed"] += 1
                else:
                    result["total_failed"] += 1
                    result["by_modifier"][modifier_name]["failed"] += 1

    result["by_modifier"] = dict(result["by_modifier"])

    return result


def aggregate_results(profile_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate results from all profiles."""
    aggregated = {
        "total_profiles": len(profile_results),
        "profiles_with_data": sum(1 for r in profile_results if r["exists"]),
        "total_generated": sum(r["total_generated"] for r in profile_results),
        "total_validated": sum(r["total_validated"] for r in profile_results),
        "total_passed": sum(r["total_passed"] for r in profile_results),
        "total_failed": sum(r["total_failed"] for r in profile_results),
        "by_modifier": defaultdict(
            lambda: {
                "generated": 0,
                "validated": 0,
                "passed": 0,
                "failed": 0,
                "f2p_counts": [],
                "p2p_counts": [],
                "profiles_used": 0,
            }
        ),
        "profile_results": profile_results,
    }

    for result in profile_results:
        if not result["exists"]:
            continue

        for modifier, data in result["by_modifier"].items():
            aggregated["by_modifier"][modifier]["generated"] += data["generated"]
            aggregated["by_modifier"][modifier]["validated"] += data["validated"]
            aggregated["by_modifier"][modifier]["passed"] += data["passed"]
            aggregated["by_modifier"][modifier]["failed"] += data["failed"]
            aggregated["by_modifier"][modifier]["f2p_counts"].extend(
                data["f2p_counts"]
            )
            aggregated["by_modifier"][modifier]["p2p_counts"].extend(
                data["p2p_counts"]
            )
            if data["generated"] > 0:
                aggregated["by_modifier"][modifier]["profiles_used"] += 1

    aggregated["by_modifier"] = dict(aggregated["by_modifier"])

    return aggregated


def print_comprehensive_report(aggregated: Dict[str, Any]) -> None:
    """Print comprehensive report."""
    print("=" * 100)
    print("COMPREHENSIVE RUST PROCEDURAL BUG GENERATION ANALYSIS")
    print("=" * 100)
    print()

    print("OVERALL STATISTICS")
    print("-" * 100)
    print(f"Total Rust profiles:                {aggregated['total_profiles']}")
    print(f"Profiles with generated bugs:       {aggregated['profiles_with_data']}")
    print(f"Total bugs generated:               {aggregated['total_generated']}")
    print(f"Total bugs validated:               {aggregated['total_validated']}")
    
    if aggregated['total_validated'] > 0:
        pass_rate = (aggregated['total_passed'] / aggregated['total_validated']) * 100
        print(f"Bugs passing validation:            {aggregated['total_passed']} ({pass_rate:.1f}%)")
        print(f"Bugs failing validation:            {aggregated['total_failed']} ({100 - pass_rate:.1f}%)")
    print()

    print("PER-MODIFIER EFFECTIVENESS")
    print("-" * 100)
    print(
        f"{'Modifier':<40} {'Generated':<12} {'Validated':<12} {'Passed':<12} {'Pass Rate':<12} {'Profiles':<10}"
    )
    print("-" * 100)

    sorted_modifiers = sorted(
        aggregated["by_modifier"].items(),
        key=lambda x: x[1]["generated"],
        reverse=True,
    )

    for modifier, data in sorted_modifiers:
        validated = data["validated"]
        passed = data["passed"]
        pass_rate = (passed / max(validated, 1)) * 100

        print(
            f"{modifier:<40} {data['generated']:<12} {validated:<12} {passed:<12} {pass_rate:>10.1f}% {data['profiles_used']:>9}"
        )

    print()

    print("TEST FAILURE DISTRIBUTION BY MODIFIER")
    print("-" * 100)
    print(
        f"{'Modifier':<40} {'Avg F2P':<12} {'Min F2P':<12} {'Max F2P':<12} {'Avg P2P':<12}"
    )
    print("-" * 100)

    for modifier, data in sorted_modifiers:
        f2p_counts = data["f2p_counts"]
        p2p_counts = data["p2p_counts"]

        if f2p_counts:
            avg_f2p = sum(f2p_counts) / len(f2p_counts)
            min_f2p = min(f2p_counts)
            max_f2p = max(f2p_counts)
            avg_p2p = sum(p2p_counts) / len(p2p_counts)

            print(
                f"{modifier:<40} {avg_f2p:<12.2f} {min_f2p:<12} {max_f2p:<12} {avg_p2p:<12.2f}"
            )

    print()

    print("PER-PROFILE SUMMARY")
    print("-" * 100)
    print(
        f"{'Repository':<50} {'Generated':<12} {'Validated':<12} {'Passed':<12} {'Pass Rate':<12}"
    )
    print("-" * 100)

    for result in aggregated["profile_results"]:
        if not result["exists"]:
            continue

        repo_name = result["repo_id"].replace("__", "/").rsplit(".", 1)[0]
        validated = result["total_validated"]
        passed = result["total_passed"]
        pass_rate = (passed / max(validated, 1)) * 100 if validated > 0 else 0

        print(
            f"{repo_name:<50} {result['total_generated']:<12} {validated:<12} {passed:<12} {pass_rate:>10.1f}%"
        )

    print()

    all_f2p = []
    all_p2p = []
    for data in aggregated["by_modifier"].values():
        all_f2p.extend(data["f2p_counts"])
        all_p2p.extend(data["p2p_counts"])

    if all_f2p:
        print("OVERALL TEST FAILURE DISTRIBUTION")
        print("-" * 100)
        print(
            f"Average tests broken per bug (F2P):     {sum(all_f2p) / len(all_f2p):.2f}"
        )
        print(
            f"Median tests broken per bug (F2P):      {sorted(all_f2p)[len(all_f2p) // 2]}"
        )
        print(f"Min tests broken per bug (F2P):         {min(all_f2p)}")
        print(f"Max tests broken per bug (F2P):         {max(all_f2p)}")
        print()
        print(
            f"Average tests maintained per bug (P2P): {sum(all_p2p) / len(all_p2p):.2f}"
        )
        print(
            f"Median tests maintained per bug (P2P):  {sorted(all_p2p)[len(all_p2p) // 2]}"
        )
        print()

    print("=" * 100)


def generate_markdown_report(aggregated: Dict[str, Any]) -> str:
    """Generate markdown report for GitHub issue."""
    md = []
    md.append("# Comprehensive Rust Procedural Bug Generation Analysis")
    md.append("")
    md.append("## Executive Summary")
    md.append("")
    
    if aggregated['total_validated'] > 0:
        pass_rate = (aggregated['total_passed'] / aggregated['total_validated']) * 100
        md.append(f"- **Total Rust Profiles Tested**: {aggregated['profiles_with_data']}/{aggregated['total_profiles']}")
        md.append(f"- **Total Bugs Generated**: {aggregated['total_generated']}")
        md.append(f"- **Total Bugs Validated**: {aggregated['total_validated']}")
        md.append(f"- **Validation Pass Rate**: {pass_rate:.1f}% ({aggregated['total_passed']}/{aggregated['total_validated']})")
    
    md.append("")
    md.append("## Key Findings")
    md.append("")
    
    sorted_modifiers = sorted(
        aggregated["by_modifier"].items(),
        key=lambda x: (x[1]["passed"] / max(x[1]["validated"], 1)),
        reverse=True,
    )
    
    if sorted_modifiers:
        best_modifier, best_data = sorted_modifiers[0]
        best_pass_rate = (best_data["passed"] / max(best_data["validated"], 1)) * 100
        md.append(f"- **Most Effective Modifier**: `{best_modifier}` with {best_pass_rate:.1f}% pass rate ({best_data['passed']}/{best_data['validated']} bugs)")
        
        most_prolific = max(aggregated["by_modifier"].items(), key=lambda x: x[1]["generated"])
        md.append(f"- **Most Prolific Modifier**: `{most_prolific[0]}` generated {most_prolific[1]['generated']} bugs across {most_prolific[1]['profiles_used']} profiles")
    
    all_f2p = []
    for data in aggregated["by_modifier"].values():
        all_f2p.extend(data["f2p_counts"])
    
    if all_f2p:
        avg_f2p = sum(all_f2p) / len(all_f2p)
        md.append(f"- **Average Tests Broken per Bug**: {avg_f2p:.2f} (F2P)")
        md.append(f"- **Test Failure Range**: {min(all_f2p)} to {max(all_f2p)} tests per bug")
    
    md.append("")
    md.append("## Per-Modifier Effectiveness")
    md.append("")
    md.append("| Modifier | Generated | Validated | Passed | Pass Rate | Profiles Used |")
    md.append("|----------|-----------|-----------|--------|-----------|---------------|")
    
    sorted_by_generated = sorted(
        aggregated["by_modifier"].items(),
        key=lambda x: x[1]["generated"],
        reverse=True,
    )
    
    for modifier, data in sorted_by_generated:
        validated = data["validated"]
        passed = data["passed"]
        pass_rate = (passed / max(validated, 1)) * 100
        md.append(
            f"| `{modifier}` | {data['generated']} | {validated} | {passed} | {pass_rate:.1f}% | {data['profiles_used']} |"
        )
    
    md.append("")
    md.append("## Test Failure Distribution by Modifier")
    md.append("")
    md.append("| Modifier | Avg F2P | Min F2P | Max F2P | Avg P2P |")
    md.append("|----------|---------|---------|---------|---------|")
    
    for modifier, data in sorted_by_generated:
        f2p_counts = data["f2p_counts"]
        p2p_counts = data["p2p_counts"]
        
        if f2p_counts:
            avg_f2p = sum(f2p_counts) / len(f2p_counts)
            min_f2p = min(f2p_counts)
            max_f2p = max(f2p_counts)
            avg_p2p = sum(p2p_counts) / len(p2p_counts)
            md.append(
                f"| `{modifier}` | {avg_f2p:.2f} | {min_f2p} | {max_f2p} | {avg_p2p:.2f} |"
            )
    
    md.append("")
    md.append("## Per-Profile Results")
    md.append("")
    md.append("| Repository | Generated | Validated | Passed | Pass Rate |")
    md.append("|------------|-----------|-----------|--------|-----------|")
    
    for result in aggregated["profile_results"]:
        if not result["exists"]:
            continue
        
        repo_name = result["repo_id"].replace("__", "/").rsplit(".", 1)[0]
        validated = result["total_validated"]
        passed = result["total_passed"]
        pass_rate = (passed / max(validated, 1)) * 100 if validated > 0 else 0
        md.append(
            f"| {repo_name} | {result['total_generated']} | {validated} | {passed} | {pass_rate:.1f}% |"
        )
    
    md.append("")
    md.append("## Methodology")
    md.append("")
    md.append("### Bug Generation")
    md.append("Bugs were generated using 10 Rust procedural modifiers across three categories:")
    md.append("- **Control Flow** (2 modifiers): `func_pm_ctrl_invert_if`, `func_pm_ctrl_shuffle`")
    md.append("- **Operations** (5 modifiers): `func_pm_op_change`, `func_pm_op_swap`, `func_pm_flip_operators`, `func_pm_break_chains`, `func_pm_change_constants`")
    md.append("- **Remove** (3 modifiers): `func_pm_remove_assign`, `func_pm_remove_cond`, `func_pm_remove_loop`")
    md.append("")
    md.append("### Validation Criteria")
    md.append("A bug passes validation if:")
    md.append("1. It creates at least one failing test (F2P > 0)")
    md.append("2. The bug is reproducible in a clean Docker environment")
    md.append("3. The patch applies cleanly to the repository")
    md.append("")
    md.append("### Quality Metrics")
    md.append("- **F2P (Fail-to-Pass)**: Number of tests that fail with the bug but pass after fixing")
    md.append("- **P2P (Pass-to-Pass)**: Number of tests that pass both with and without the bug")
    md.append("- **Pass Rate**: Percentage of generated bugs that pass validation")
    md.append("")
    md.append("## Commands Used")
    md.append("")
    md.append("```bash")
    md.append("# Run bug generation and validation for all Rust profiles")
    md.append("./scripts/test_rust_procedural.sh 50")
    md.append("")
    md.append("# Analyze individual profile")
    md.append("python scripts/analyze_bugs.py <repo_id>")
    md.append("")
    md.append("# Generate comprehensive report")
    md.append("python scripts/analyze_rust_comprehensive.py")
    md.append("```")
    md.append("")
    
    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive analysis of Rust procedural bug generation"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file for detailed JSON report (default: logs/analysis/rust_comprehensive.json)",
    )
    parser.add_argument(
        "--markdown",
        "-m",
        type=str,
        default=None,
        help="Output file for markdown report (default: logs/analysis/rust_comprehensive.md)",
    )

    args = parser.parse_args()

    print("Analyzing all Rust profiles...")
    print()

    profile_results = []
    for repo_id in RUST_PROFILES:
        result = analyze_single_profile(repo_id)
        profile_results.append(result)
        if result["exists"]:
            print(f"✓ {repo_id}: {result['total_generated']} generated, {result['total_passed']}/{result['total_validated']} passed")
        else:
            print(f"⊘ {repo_id}: No data found")

    print()

    aggregated = aggregate_results(profile_results)

    print_comprehensive_report(aggregated)

    if args.output is None:
        output_dir = Path("logs/analysis")
        output_dir.mkdir(parents=True, exist_ok=True)
        args.output = str(output_dir / "rust_comprehensive.json")

    with open(args.output, "w") as f:
        json.dump(aggregated, f, indent=2)
    print(f"\nDetailed JSON report saved to: {args.output}")

    if args.markdown is None:
        output_dir = Path("logs/analysis")
        output_dir.mkdir(parents=True, exist_ok=True)
        args.markdown = str(output_dir / "rust_comprehensive.md")

    markdown_content = generate_markdown_report(aggregated)
    with open(args.markdown, "w") as f:
        f.write(markdown_content)
    print(f"Markdown report saved to: {args.markdown}")


if __name__ == "__main__":
    main()
