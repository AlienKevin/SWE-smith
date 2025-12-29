"""
Modal Bug Generation & Validation Script

Supports two modes:
1. Generation + Validation: Generate bugs remotely, then validate them
2. Validate-only: Validate existing patches from local logs

Both modes run pre-gold and post-gold tests in parallel across all repos.
"""

import argparse
import asyncio
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import modal
modal.enable_output()

# ============================================================================
# Constants & Configuration
# ============================================================================

APP_NAME = "swesmith-bug-gen"
MINUTES = 60
MODAL_TIMEOUT = 10 * MINUTES

LANGUAGE_TO_BASE_CLASS = {
    "python": "PythonProfile",
    "javascript": "JavaScriptProfile",
    "typescript": "JavaScriptProfile",
    "golang": "GoProfile",
    "go": "GoProfile",
    "rust": "RustProfile",
    "java": "JavaProfile",
    "c": "CProfile",
    "cpp": "CppProfile",
    "csharp": "CSharpProfile",
    "php": "PhpProfile",
}

TEST_OUTPUT_START = ">>>>> Start Test Output"
TEST_OUTPUT_END = ">>>>> End Test Output"
PREGOLD_TIMEOUT = 200  # seconds - skip post-gold if baseline exceeds this
MIN_PATCHES_FOR_VALIDATION = 50  # skip repos with fewer patches

# ============================================================================
# Profile & Repo Utilities
# ============================================================================

def get_repos_for_language(language: str) -> list[str]:
    """Get all registered repos for a given language."""
    from swesmith.profiles import registry
    
    base_class_name = LANGUAGE_TO_BASE_CLASS.get(language.lower())
    if not base_class_name:
        raise ValueError(f"Unknown language: {language}. Supported: {list(LANGUAGE_TO_BASE_CLASS.keys())}")
    
    return [
        f"{profile.owner}/{profile.repo}"
        for profile in registry.values()
        if profile.__class__.__name__ != base_class_name
        and base_class_name in [base.__name__ for base in profile.__class__.__mro__]
    ]


def resolve_profile(repo_name: str):
    """Resolve a profile from repo name using robust lookup."""
    from swesmith.profiles import registry
    
    try:
        return registry.get(repo_name)
    except KeyError:
        for key in registry.keys():
            try:
                p = registry.get(key)
                if f"{p.owner}/{p.repo}" == repo_name:
                    return p
            except Exception:
                continue
    raise RuntimeError(f"No profile found for repo: {repo_name}")


# ============================================================================
# Modal Setup & Images
# ============================================================================

generator_image = (
    modal.Image.from_registry("ubuntu:22.04", add_python="3.11")
    .apt_install("git")
    .pip_install_from_pyproject("pyproject.toml", optional_dependencies=["generate"])
    .env({"PYTHONPATH": "/root"})
    .add_local_dir("swesmith", remote_path="/root/swesmith")
    .add_local_file(".env", remote_path="/root/.env")
)

_validator_image_cache: dict[str, modal.Image] = {}


def get_validator_image(image_name: str) -> modal.Image:
    """Get or create a validator image for the given Docker image name."""
    if image_name not in _validator_image_cache:
        _validator_image_cache[image_name] = (
            modal.Image.from_registry(image_name, add_python="3.11")
            .pip_install_from_pyproject("pyproject.toml", optional_dependencies=["validate"])
            .env({"PYTHONPATH": "/root"})
            .add_local_dir("swesmith", remote_path="/root/swesmith")
        )
    return _validator_image_cache[image_name]


app = modal.App(APP_NAME)


# ============================================================================
# Remote Bug Generation
# ============================================================================

@app.function(
    image=generator_image,
    secrets=[modal.Secret.from_name("GITHUB_TOKEN")],
    timeout=MODAL_TIMEOUT,
)
def generate_bugs_remote(
    repo_name: str, max_bugs: int, interleave: bool,
    max_entities: int, max_candidates: int, timeout_buffer_seconds: int = 15
) -> dict:
    """Generate bugs for a repository on a remote Modal worker."""
    import sys
    from io import StringIO

    if "/root" not in sys.path:
        sys.path.append("/root")

    from swesmith.profiles import registry
    from swesmith.bug_gen.procedural.generate import main as generate_main
    from swesmith.bug_gen.collect_patches import main as collect_patches_main

    # Setup output capture
    log_buffer = StringIO()
    original_stdout, original_stderr = sys.stdout, sys.stderr
    artifacts = {}

    class TeeWriter:
        def __init__(self, buffer, original):
            self.buffer, self.original = buffer, original
        def write(self, data):
            self.buffer.write(data)
            self.original.write(data)
        def flush(self):
            self.buffer.flush()
            self.original.flush()

    sys.stdout = TeeWriter(log_buffer, original_stdout)
    sys.stderr = TeeWriter(log_buffer, original_stderr)

    # Resolve repo ID
    def resolve_repo_id():
        try:
            return registry.get_from_inst({"repo": repo_name, "instance_id": "dummy"}).repo_name
        except Exception as e:
            print(f"Direct profile lookup failed for {repo_name}: {e}")
            target = repo_name.replace("/", "__")
            candidates = [key for key in registry.keys() if target in key]
            return candidates[0] if candidates else repo_name

    repo_id = resolve_repo_id()
    print(f"Resolved repo_id: {repo_id}")
    logs_base = Path("logs/bug_gen")

    def _safe_execute(func, error_msg, *args, **kwargs):
        import traceback
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"{error_msg}: {e}")
            traceback.print_exc()
            return None

    def collect_results():
        if not logs_base.exists():
            print(f"LOGS BASE MISSING: {logs_base}")
            return

        generated_dirs = [d for d in logs_base.iterdir() if d.is_dir()]
        if not generated_dirs:
            print(f"NO DATA IN LOGS BASE. Files: {list(logs_base.glob('**/*'))}")
            return

        repo_id_actual = sorted(generated_dirs, key=lambda x: x.stat().st_mtime, reverse=True)[0].name
        print(f"Detected repo_id_actual: {repo_id_actual}")

        _safe_execute(collect_patches_main, "Error in collect_patches_main", str(logs_base / repo_id_actual))

        # Zip and save
        def _zip():
            shutil.make_archive(f"/tmp/{repo_id_actual}", 'zip', str(logs_base / repo_id_actual))
            with open(f"/tmp/{repo_id_actual}.zip", "rb") as f:
                artifacts["bug_gen_zip"] = f.read()
            print(f"Created bug_gen_zip: {len(artifacts['bug_gen_zip'])} bytes")
        _safe_execute(_zip, "Error creating bug_gen_zip")

        patches_file = logs_base / f"{repo_id_actual}_all_patches.json"
        if patches_file.exists():
            artifacts["patches_json"] = patches_file.read_text()
            print(f"Read patches_json: {len(artifacts['patches_json'])} bytes")
        else:
            print(f"Patches file not found. Available: {[p.name for p in logs_base.iterdir()]}")

    soft_timeout = MODAL_TIMEOUT - timeout_buffer_seconds
    print(f"Soft timeout: {soft_timeout}s")

    try:
        generate_main(
            repo=repo_id, max_bugs=max_bugs, seed=24, interleave=interleave,
            max_entities=max_entities, max_candidates=max_candidates,
            timeout_seconds=soft_timeout
        )
    except Exception as e:
        import traceback
        print(f"Error in generate_main: {e}")
        traceback.print_exc()
    finally:
        sys.stdout, sys.stderr = original_stdout, original_stderr
        print("\nCollecting partial results...")
        _safe_execute(collect_results, "Error collecting results")
        artifacts["modal_output_log"] = log_buffer.getvalue()
        if not logs_base.exists():
            artifacts["error"] = f"Logs directory {logs_base} does not exist."

    return artifacts


# ============================================================================
# Validation Sandbox
# ============================================================================
async def run_validation_in_sandbox(
    semaphore: asyncio.Semaphore, app: modal.App, image_name: str, instance_id: str,
    test_cmd: str, workdir: str, patch: str | None, timeout: int
) -> dict:
    """
    Run validation in a Modal Sandbox with a specific Docker image.
    
    Uses Modal's native async APIs:
    - Sandbox.create.aio() - async sandbox creation
    - process.stdout.read.aio() - async output reading  
    - process.wait.aio() - async wait for completion
    - sb.terminate.aio() - async cleanup
    
    This is pure async I/O with zero thread overhead.
    """
    async with semaphore:
        validator_image = get_validator_image(image_name)
        
        script_lines = [
            "#!/bin/bash", "exec 2>&1", "set -uxo pipefail",
            f"cd {workdir}", "git checkout .",
        ]
        
        if patch:
            script_lines.extend([
                f"cat > /tmp/{instance_id}.diff << 'PATCH_EOF'",
                patch, "PATCH_EOF",
                f"git apply /tmp/{instance_id}.diff",
            ])
        
        script_lines.extend([
            f": '{TEST_OUTPUT_START}'",
            f"{test_cmd} || true",
            f": '{TEST_OUTPUT_END}'",
        ])
        
        try:
            # Use Modal's native async APIs
            sb = await modal.Sandbox.create.aio(app=app, image=validator_image, timeout=timeout)
            process = await sb.exec.aio("bash", "-c", "\n".join(script_lines))
            try:
                output_raw = await process.stdout.read.aio()
            except UnicodeDecodeError as e:
                return {"instance_id": instance_id, "error": f"Binary output (decode failed at pos {e.start})"}
            exit_code = await process.wait.aio()
            await sb.terminate.aio()
            
            output = output_raw.decode("utf-8", errors="replace") if isinstance(output_raw, bytes) else output_raw
            return {"instance_id": instance_id, "output": output, "exit_code": exit_code}
        except UnicodeDecodeError as e:
            return {"instance_id": instance_id, "error": f"Binary output (decode failed at pos {e.start})"}
        except Exception as e:
            err_str = str(e)
            if "timeout" in err_str.lower() or "SandboxTimeoutError" in err_str:
                return {"instance_id": instance_id, "error": f"Timeout ({timeout}s)"}
            return {"instance_id": instance_id, "error": err_str}


# ============================================================================
# Generation Phase
# ============================================================================

def spawn_generation_task(repo_name: str, max_bugs: int, interleave: bool, max_entities: int, max_candidates: int):
    """Spawn a generation task without blocking."""
    try:
        profile = resolve_profile(repo_name)
        print(f"Spawning generation for {repo_name} (profile: {profile.__class__.__name__})...")
        handle = generate_bugs_remote.spawn(
            repo_name=repo_name, max_bugs=max_bugs, interleave=interleave,
            max_entities=max_entities, max_candidates=max_candidates
        )
        return (repo_name, profile.repo_name, handle)
    except Exception as e:
        return (repo_name, None, {"repo": repo_name, "error": f"Failed to resolve profile: {e}"})


def process_generation_result(repo_name: str, repo_id: str, results: dict) -> dict:
    """Process results from a completed generation task."""
    local_bug_dir = Path(f"logs/bug_gen/{repo_id}")
    local_bug_dir.mkdir(parents=True, exist_ok=True)

    # Save logs if available
    if results.get("modal_output_log"):
        (local_bug_dir / "modal_output.log").write_text(results["modal_output_log"], errors='replace')

    if "error" in results:
        print(f"Error during bug generation for {repo_name}: {results['error']}")
        return {"repo": repo_name, "repo_id": repo_id, "error": results["error"]}

    if "patches_json" not in results:
        print(f"Warning: No patches_json returned for {repo_name}")
        if "bug_gen_zip" in results:
            zip_path = local_bug_dir / "bugs.zip"
            zip_path.write_bytes(results["bug_gen_zip"])
            subprocess.run(["unzip", "-o", str(zip_path), "-d", str(local_bug_dir)], check=True)
        return {"repo": repo_name, "repo_id": repo_id, "error": "No patches_json returned"}

    patches = json.loads(results["patches_json"])
    if not patches:
        print(f"No bugs generated for {repo_name}.")
        return {"repo": repo_name, "repo_id": repo_id, "patches": [], "total_bugs": 0}

    # Save patches
    (local_bug_dir.parent / f"{repo_id}_all_patches.json").write_text(results["patches_json"])

    if "bug_gen_zip" in results:
        zip_path = local_bug_dir / "bugs.zip"
        zip_path.write_bytes(results["bug_gen_zip"])
        subprocess.run(["unzip", "-o", str(zip_path), "-d", str(local_bug_dir)], check=True)
        zip_path.unlink()

    print(f"Generated {len(patches)} bugs for {repo_name}")
    return {"repo": repo_name, "repo_id": repo_id, "patches": patches, "total_bugs": len(patches)}


def run_generation_phase(repos: list[str], args) -> list[dict]:
    """Run bug generation for all repos in parallel."""
    print(f"{'#'*60}")
    print(f"# PHASE 1: BUG GENERATION ({len(repos)} repos)")
    print(f"{'#'*60}\n")

    spawn_results = [
        spawn_generation_task(repo, args.max_bugs, args.interleave, args.max_entities, args.max_candidates)
        for repo in repos
    ]
    print(f"Spawned {len(spawn_results)} generation tasks. Waiting for results...\n")

    generation_results = []
    for repo_name, repo_id, handle_or_error in spawn_results:
        if isinstance(handle_or_error, dict):
            generation_results.append(handle_or_error)
        else:
            try:
                results = handle_or_error.get()
                generation_results.append(process_generation_result(repo_name, repo_id, results))
            except Exception as e:
                generation_results.append({"repo": repo_name, "repo_id": repo_id, "error": f"Generation failed: {e}"})

    return generation_results


# ============================================================================
# Validation Phase
# ============================================================================

def annotate_patches(patches: list, repo: str, repo_id: str, profile) -> list:
    """Add metadata to patches for validation."""
    for p in patches:
        p["_repo"] = repo
        p["_repo_id"] = repo_id
        p["_profile"] = profile
    return patches


def collect_patches_from_files(repos: list[str]) -> list[dict]:
    """Collect patches from local files for validate-only mode."""
    all_patches = []
    for repo in repos:
        try:
            profile = resolve_profile(repo)
        except Exception:
            print(f"  Skipping {repo}: profile not found")
            continue

        repo_id = profile.repo_name
        patches_file = Path(f"logs/bug_gen/{repo_id}_all_patches.json")
        if patches_file.exists():
            patches = json.loads(patches_file.read_text())
            all_patches.extend(annotate_patches(patches, repo, repo_id, profile))
            print(f"  {repo}: {len(patches)} patches")
        else:
            print(f"  Skipping {repo}: no patches file")
    return all_patches


def collect_patches_from_generation(generation_results: list[dict]) -> tuple[list[dict], list[dict]]:
    """Collect patches from generation results, separating errors."""
    all_patches, errors = [], []
    for gen_result in generation_results:
        if "error" in gen_result:
            errors.append(gen_result)
            continue
        patches = gen_result.get("patches", [])
        if patches:
            profile = resolve_profile(gen_result["repo"])
            all_patches.extend(annotate_patches(patches, gen_result["repo"], gen_result["repo_id"], profile))
    return all_patches, errors


def build_repos_with_patches(all_patches: list) -> dict:
    """Build repos_with_patches dict from annotated patches."""
    repos = {}
    for p in all_patches:
        repo = p["_repo"]
        if repo not in repos:
            repos[repo] = {"profile": p["_profile"], "repo_id": p["_repo_id"]}
    return repos


def process_postgold_result(task: dict, result: dict, get_valid_report) -> dict:
    """Process a single post-gold test result."""
    instance_id, repo, repo_id = task["instance_id"], task["repo"], task["repo_id"]
    
    if "error" in result:
        return {"instance_id": instance_id, "repo": repo, "error": result["error"], "valid": False}
    
    # Save output
    inst_log_dir = Path(f"logs/run_validation/{repo_id}/{instance_id}")
    inst_log_dir.mkdir(parents=True, exist_ok=True)
    (inst_log_dir / "test_output.txt").write_text(result["output"], errors='replace')
    
    # Check baseline
    baseline_path = f"logs/run_validation/{repo_id}/{repo_id}.ref/test_output.txt"
    if not os.path.exists(baseline_path):
        return {"instance_id": instance_id, "repo": repo, "error": f"Baseline not found", "valid": False}
    
    # Grade
    try:
        report = get_valid_report(
            val_pregold_path=baseline_path,
            val_postgold_path=str(inst_log_dir / "test_output.txt"),
            instance=task["full_patch"]
        )
        (inst_log_dir / "report.json").write_text(json.dumps(report, indent=4))
        is_valid = len(report.get("PASS_TO_FAIL", [])) > 0
        return {"instance_id": instance_id, "repo": repo, "valid": is_valid}
    except Exception as e:
        return {"instance_id": instance_id, "repo": repo, "error": f"Grading error: {e}", "valid": False}


async def run_pregold_phase_async(repos_with_patches: dict, max_concurrent: int, env_name: str) -> set[str]:
    """Run all pre-gold (baseline) tests asynchronously. Returns set of repos with 0 passing tests (to skip)."""
    from swesmith.harness.grading import read_test_output
    from swebench.harness.constants import TestStatus
    
    print(f"\nPHASE: PRE-GOLD (BASELINE) TESTS")
    print(f"Running {len(repos_with_patches)} baselines, max concurrent: {max_concurrent}")
    
    tasks = []
    previously_failed = set()  # Repos that failed in previous runs
    
    for repo, info in repos_with_patches.items():
        baseline_dir = Path(f"logs/run_validation/{info['repo_id']}/{info['repo_id']}.ref")
        test_output_exists = (baseline_dir / "test_output.txt").exists()
        error_exists = (baseline_dir / "error.txt").exists()
        
        if test_output_exists and not error_exists:
            print(f"  Skipping {repo}: baseline exists")
        elif error_exists:
            print(f"  Skipping {repo}: previously failed")
            previously_failed.add(repo)
        else:
            tasks.append({
                "repo": repo, "repo_id": info["repo_id"], "profile": info["profile"],
                "instance_id": f"{info['repo_id']}.ref", "workdir": f"/{env_name}"
            })
    
    if not tasks:
        print("  All baselines already exist!\\n")
        return previously_failed  # Return previously failed repos to skip in post-gold
    
    # Semaphore controls max concurrent operations
    semaphore = asyncio.Semaphore(max_concurrent)
    failed_repos = previously_failed.copy()  # Start with previously failed repos
    
    async def process_baseline(task: dict) -> tuple[dict, dict]:
        """Process a single baseline test."""
        result = await run_validation_in_sandbox(
            semaphore=semaphore, app=app,
            image_name=task["profile"].image_name, instance_id=task["instance_id"],
            test_cmd=task["profile"].test_cmd, workdir=task["workdir"],
            patch=None, timeout=PREGOLD_TIMEOUT
        )
        return (task, result)
    
    # Create all async tasks
    async_tasks = [process_baseline(t) for t in tasks]
    
    # Process results as they complete
    completed = 0
    for coro in asyncio.as_completed(async_tasks):
        task, result = await coro
        completed += 1
        
        try:
            baseline_dir = Path(f"logs/run_validation/{task['repo_id']}/{task['instance_id']}")
            baseline_dir.mkdir(parents=True, exist_ok=True)
            
            if "error" not in result:
                output_path = baseline_dir / "test_output.txt"
                output_path.write_text(result["output"], errors='replace')
                
                # Validate baseline has at least 1 passing test
                try:
                    test_output, found = read_test_output(str(output_path))
                    if found and test_output:
                        status_map = task["profile"].log_parser(test_output)
                        passed = sum(1 for s in status_map.values() if s == TestStatus.PASSED.value)
                        if passed == 0:
                            status = f"⚠️ 0 tests passed (skipping post-gold)"
                            failed_repos.add(task["repo"])
                            # Write error file so this repo is skipped next time
                            (baseline_dir / "error.txt").write_text(f"Pre-gold failed: 0 tests passed")
                        else:
                            status = f"OK ({passed} tests passed)"
                    else:
                        # Diagnose why test output wasn't found
                        raw_output = result["output"]
                        if "APPLY_PATCH_FAIL" in raw_output or "error: patch failed" in raw_output:
                            reason = "patch apply failed"
                        elif TEST_OUTPUT_START not in raw_output:
                            reason = "test command crashed before start marker"
                        elif TEST_OUTPUT_END not in raw_output:
                            reason = "tests never completed (no end marker)"
                        elif not test_output:
                            reason = "no test output between markers"
                        else:
                            reason = "unknown"
                        status = f"⚠️ {reason} (skipping post-gold)"
                        failed_repos.add(task["repo"])
                        # Write error file so this repo is skipped next time
                        (baseline_dir / "error.txt").write_text(f"Pre-gold failed: {reason}")
                except Exception as e:
                    status = f"OK (parse check failed: {e})"
            else:
                status = f"ERROR: {result['error'][:50]}"
                failed_repos.add(task["repo"])
                # Write error file so this repo is skipped next time
                (baseline_dir / "error.txt").write_text(f"Pre-gold sandbox error: {result['error']}")
        except Exception as e:
            status = f"EXCEPTION: {e}"
            failed_repos.add(task["repo"])
            # Try to write error file
            try:
                baseline_dir = Path(f"logs/run_validation/{task['repo_id']}/{task['instance_id']}")
                baseline_dir.mkdir(parents=True, exist_ok=True)
                (baseline_dir / "error.txt").write_text(f"Pre-gold exception: {e}")
            except:
                pass
        print(f"  [{completed}/{len(tasks)}] {task['repo']}: {status}")
    
    print(f"Pre-gold complete: {completed} baselines")
    if failed_repos:
        print(f"  ⚠️ {len(failed_repos)} repos will be skipped in post-gold")
    print()
    return failed_repos


def run_pregold_phase(repos_with_patches: dict, max_concurrent: int, env_name: str) -> set[str]:
    """Sync wrapper for the async pre-gold phase."""
    return asyncio.run(run_pregold_phase_async(repos_with_patches, max_concurrent, env_name))


async def run_postgold_phase_async(all_patches: list, max_concurrent: int, env_name: str) -> list[dict]:
    """
    Run all post-gold tests using asyncio for efficient concurrent I/O.
    
    Uses asyncio.Semaphore to limit concurrency instead of ThreadPoolExecutor.
    This is much more efficient for I/O-bound operations like Modal API calls:
    - ThreadPoolExecutor with 1000 workers = 1000 threads = high memory/CPU overhead
    - asyncio with semaphore = 1 thread + event loop = minimal overhead
    """
    from swesmith.harness.grading import get_valid_report
    
    print(f"PHASE: POST-GOLD TESTS")
    print(f"Running {len(all_patches)} patches, max concurrent: {max_concurrent}")
    
    tasks = [
        {"repo": p["_repo"], "repo_id": p["_repo_id"], "profile": p["_profile"],
         "instance_id": p["instance_id"], "patch": p["patch"],
         "workdir": f"/{env_name}", "full_patch": p}
        for p in all_patches
        if not Path(f"logs/run_validation/{p['_repo_id']}/{p['instance_id']}/report.json").exists()
    ]
    
    print(f"  {len(all_patches) - len(tasks)} already validated, {len(tasks)} remaining")
    
    if not tasks:
        print("  All patches already validated!")
        return []
    
    # Semaphore controls max concurrent operations
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_single_task(task: dict) -> dict:
        """Process a single validation task."""
        result = await run_validation_in_sandbox(
            semaphore=semaphore, app=app,
            image_name=task["profile"].image_name, instance_id=task["instance_id"],
            test_cmd=task["profile"].test_cmd, workdir=task["workdir"],
            patch=task["patch"], timeout=task["profile"].timeout
        )
        return (task, result)
    
    # Create all async tasks
    async_tasks = [process_single_task(t) for t in tasks]
    
    # Track progress
    results = []
    completed = 0
    valid_count = 0
    
    # Process results as they complete
    for coro in asyncio.as_completed(async_tasks):
        task, result = await coro
        completed += 1
        
        try:
            processed = process_postgold_result(task, result, get_valid_report)
        except Exception as e:
            processed = {"instance_id": task["instance_id"], "repo": task["repo"], "error": str(e), "valid": False}
        
        results.append(processed)
        if processed.get("valid"):
            valid_count += 1
        if completed % 100 == 0 or completed == len(tasks):
            print(f"  Progress: {completed}/{len(tasks)} tests, {valid_count} valid bugs")
    
    print(f"Post-gold complete: {valid_count}/{len(tasks)} valid bugs\n")
    return results


def run_postgold_phase(all_patches: list, max_concurrent: int, env_name: str) -> list[dict]:
    """Sync wrapper for the async post-gold phase."""
    return asyncio.run(run_postgold_phase_async(all_patches, max_concurrent, env_name))


def run_validation_phase(all_patches: list, max_concurrent: int, env_name: str) -> list[dict]:
    """Run complete validation (pre-gold + post-gold). Existing baselines are skipped automatically."""
    if not all_patches:
        print("No patches to validate.")
        return []
    
    # Count patches per repo and filter out repos with too few patches
    repo_patch_counts = {}
    for p in all_patches:
        repo = p["_repo"]
        repo_patch_counts[repo] = repo_patch_counts.get(repo, 0) + 1
    
    small_repos = {repo for repo, count in repo_patch_counts.items() if count < MIN_PATCHES_FOR_VALIDATION}
    if small_repos:
        original_count = len(all_patches)
        all_patches = [p for p in all_patches if p["_repo"] not in small_repos]
        print(f"Skipping {len(small_repos)} repos with <{MIN_PATCHES_FOR_VALIDATION} patches: {', '.join(sorted(small_repos))}")
        print(f"Filtered out {original_count - len(all_patches)} patches\n")
    
    if not all_patches:
        print("No patches remaining after filtering.")
        return []
    
    repos_with_patches = build_repos_with_patches(all_patches)
    failed_repos = run_pregold_phase(repos_with_patches, max_concurrent, env_name)
    
    # Filter out patches from repos with broken baselines
    if failed_repos:
        original_count = len(all_patches)
        all_patches = [p for p in all_patches if p["_repo"] not in failed_repos]
        print(f"Filtered out {original_count - len(all_patches)} patches from {len(failed_repos)} repos with broken baselines")
    
    return run_postgold_phase(all_patches, max_concurrent, env_name)


def print_summary(results: list[dict], repos_count: int):
    """Print validation summary."""
    valid_count = sum(1 for r in results if r.get("valid"))
    
    print(f"\n{'='*60}")
    print(f"RESULTS: {valid_count} valid bugs out of {len(results)} patches")
    print(f"{'='*60}")
    
    repo_stats = {}
    for r in results:
        repo = r["repo"]
        if repo not in repo_stats:
            repo_stats[repo] = {"total": 0, "valid": 0, "errors": 0}
        repo_stats[repo]["total"] += 1
        if r.get("valid"):
            repo_stats[repo]["valid"] += 1
        if "error" in r:
            repo_stats[repo]["errors"] += 1
    
    print("\nPer-repo breakdown:")
    for repo, stats in sorted(repo_stats.items()):
        err = f" ({stats['errors']} errors)" if stats['errors'] else ""
        print(f"  {repo}: {stats['valid']}/{stats['total']} valid{err}")
    
    print(f"\nTotal: {valid_count}/{len(results)} valid bugs across {repos_count} repos")


# ============================================================================
# CLI & Main
# ============================================================================

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Modal Bug Generation & Validation")
    parser.add_argument("--repos", nargs="*", help="Repository names (owner/repo)")
    parser.add_argument("--language", default="javascript", help="Language (default: javascript)")
    parser.add_argument("--max-bugs", type=int, default=200, help="Max bugs per modifier")
    parser.add_argument("--interleave", action="store_true", help="Interleave modifiers")
    parser.add_argument("--max-entities", type=int, default=2000, help="Max entities to sample (-1 for all)")
    parser.add_argument("--max-candidates", type=int, default=2000, help="Max candidates to process (-1 for all)")
    parser.add_argument("--validate-only", action="store_true", help="Only validate existing patches")
    parser.add_argument("--max-concurrent-tests", type=int, default=400, help="Max concurrent tests (default: 400)")
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Determine repos
    if args.repos:
        repos = args.repos
    else:
        repos = get_repos_for_language(args.language)
        print(f"Found {len(repos)} repos for '{args.language}':")
        for r in repos:
            print(f"  - {r}")
    
    if not repos:
        print(f"No repos found for language: {args.language}")
        exit(1)
    
    print(f"\n{'='*60}")
    print(f"BUG GEN - {len(repos)} repos, {args.max_concurrent_tests} max concurrent")
    print(f"{'='*60}\n")
    
    with app.run():
        from swesmith.constants import ENV_NAME
        
        if args.validate_only:
            print("MODE: Validation only\n")
            print("Collecting patches...")
            all_patches = collect_patches_from_files(repos)
            print(f"\nTotal: {len(all_patches)} patches\n")
            
            results = run_validation_phase(all_patches, args.max_concurrent_tests, ENV_NAME)
            if results:
                print_summary(results, len(build_repos_with_patches(all_patches)))
        
        else:
            print("MODE: Generation + Validation\n")
            
            generation_results = run_generation_phase(repos, args)
            
            print(f"\n{'#'*60}")
            print(f"# PHASE 2: VALIDATION")
            print(f"{'#'*60}\n")
            
            all_patches, errors = collect_patches_from_generation(generation_results)
            results = run_validation_phase(all_patches, args.max_concurrent_tests, ENV_NAME)
            
            if results:
                print_summary(results, len(build_repos_with_patches(all_patches)))
            
            if errors:
                print(f"\nGeneration Errors ({len(errors)}):")
                for err in errors:
                    print(f"  - {err['repo']}: {err.get('error', 'Unknown')}")


if __name__ == "__main__":
    main()
