import argparse
import os
import shutil
import json
import subprocess
from pathlib import Path

import modal
modal.enable_output()  # Enable detailed build logs

# Constants
APP_NAME = "swesmith-bug-gen"
MINUTES = 60

# Mapping from language name to profile base class name
LANGUAGE_TO_BASE_CLASS = {
    "python": "PythonProfile",
    "javascript": "JavaScriptProfile",
    "typescript": "JavaScriptProfile",  # TypeScript uses JavaScriptProfile
    "golang": "GoProfile",
    "go": "GoProfile",
    "rust": "RustProfile",
    "java": "JavaProfile",
    "c": "CProfile",
    "cpp": "CppProfile",
    "csharp": "CSharpProfile",
    "php": "PhpProfile",
}


def get_repos_for_language(language: str) -> list[str]:
    """Get all registered repos for a given language."""
    from swesmith.profiles import registry
    
    base_class_name = LANGUAGE_TO_BASE_CLASS.get(language.lower())
    if not base_class_name:
        raise ValueError(f"Unknown language: {language}. Supported: {list(LANGUAGE_TO_BASE_CLASS.keys())}")
    
    repos = []
    # Get unique profile classes (values() returns unique profiles)
    for profile in registry.values():
        # Check if the profile class is a subclass of the language-specific base class
        if profile.__class__.__name__ != base_class_name and base_class_name in [
            base.__name__ for base in profile.__class__.__mro__
        ]:
            repos.append(f"{profile.owner}/{profile.repo}")
    return repos


def resolve_profile(repo_name: str):
    """Resolve a profile from repo name using robust lookup."""
    from swesmith.profiles import registry
    
    profile = None
    
    # Try direct lookup first
    try:
        profile = registry.get(repo_name)
    except KeyError:
        # Try owner/repo match
        for key in registry.keys():
            try:
                p = registry.get(key)
                if f"{p.owner}/{p.repo}" == repo_name:
                    profile = p
                    break
            except Exception:
                continue
    
    if not profile:
        raise RuntimeError(f"No profile found for repo: {repo_name}")
    
    return profile



# Generator Image: For procedural generation
# Use minimal 'generate' dependency group to avoid heavy packages like sglang, litellm, openai, etc.
generator_image = (
    modal.Image.from_registry("ubuntu:22.04", add_python="3.11")
    .apt_install("git")
    .pip_install_from_pyproject("pyproject.toml", optional_dependencies=["generate"])
    .env({"PYTHONPATH": "/root"})
    .add_local_dir("swesmith", remote_path="/root/swesmith")
    .add_local_file(".env", remote_path="/root/.env")
)

# Cache for dynamically created validator images
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


@app.function(
    image=generator_image,
    secrets=[modal.Secret.from_name("GITHUB_TOKEN")],
    timeout=5 * MINUTES,
)
def generate_bugs_remote(repo_name: str, max_bugs: int, interleave: bool) -> dict:
    """
    Generates bugs for the repository on a remote Modal worker.
    """
    import os
    import sys
    # Add /root to sys.path to be double sure
    if "/root" not in sys.path:
        sys.path.append("/root")

    from swesmith.profiles import registry
    from swesmith.bug_gen.procedural.generate import main as generate_main
    from swesmith.bug_gen.collect_patches import main as collect_patches_main
    import traceback

    print(f"CWD: {os.getcwd()}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")
    print(f"Starting bug generation for {repo_name}...")
    
    # Identify Repo ID
    try:
        # Try direct lookup first
        profile = registry.get_from_inst({"repo": repo_name, "instance_id": "dummy"})
        repo_id = profile.repo_name 
    except Exception as e:
        print(f"Direct profile lookup failed for {repo_name}: {e}")
        # Search registry for matching key
        candidates = []
        target = repo_name.replace("/", "__")
        for key in registry.keys():
            if target in key:
                candidates.append(key)
        
        if candidates:
            repo_id = candidates[0]
            print(f"Resolved {repo_name} to profile key {repo_id}")
        else:
            print(f"Warning: No matching profile found for {repo_name} in registry. Using original name.")
            repo_id = repo_name 

    try:
        print(f"Calling generate_main with repo={repo_id}, max_bugs={max_bugs}...")
        generate_main(
            repo=repo_id,
            max_bugs=max_bugs,
            seed=24,
            interleave=interleave
        )
    except Exception as e:
        print(f"Error in generate_main: {e}")
        return {"error": str(e), "traceback": traceback.format_exc()}

    # Collect patches
    logs_base = Path("logs/bug_gen")
    if not logs_base.exists():
         print(f"LOGS BASE MISSING: {logs_base}")
         # Maybe it's in the current dir?
         if Path(repo_id).exists():
              print(f"Found repo dir {repo_id} in current dir, but logs/bug_gen is missing.")
         return {"error": f"Logs directory {logs_base} does not exist."}
         
    generated_repo_dirs = [d for d in logs_base.iterdir() if d.is_dir()]
    if not generated_repo_dirs:
         files = [str(p) for p in logs_base.glob("**/*")]
         print(f"NO DATA IN LOGS BASE. Files found: {files}")
         return {"error": f"No bug generation directory found in {logs_base}."}
    
    # Sort to pick the most recently created repo dir if multiple exist
    generated_repo_dirs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    repo_id_actual = generated_repo_dirs[0].name
    print(f"Detected repo_id_actual: {repo_id_actual}")
    
    # Run collection
    collect_patches_main(str(logs_base / repo_id_actual))
    
    # Read artifacts
    artifacts = {}
    
    # Zip the bug gen dir
    shutil.make_archive(f"/tmp/{repo_id_actual}", 'zip', str(logs_base / repo_id_actual))
    with open(f"/tmp/{repo_id_actual}.zip", "rb") as f:
        artifacts["bug_gen_zip"] = f.read()
        
    # Get the all_patches.json
    patches_file = logs_base / f"{repo_id_actual}_all_patches.json"
    if patches_file.exists():
        with open(patches_file, "r") as f:
            artifacts["patches_json"] = f.read()
            print(f"Successfully read patches_json: {len(artifacts['patches_json'])} bytes")
    else:
        existing_files = [str(p.name) for p in logs_base.iterdir()]
        print(f"Patches file {patches_file} not found. Available: {existing_files}")
            
    return artifacts


# Markers for parsing test output
TEST_OUTPUT_START = ">>>>> Start Test Output"
TEST_OUTPUT_END = ">>>>> End Test Output"


def run_validation_in_sandbox(
    app: modal.App,
    image_name: str,
    instance_id: str,
    test_cmd: str,
    workdir: str,
    patch: str | None = None,
    timeout: int = 300,
) -> dict:
    """
    Run validation in a Modal Sandbox with a specific Docker image.
    This allows running code in any container without pre-registering functions.
    """
    validator_image = get_validator_image(image_name)
    
    # Build the script to run inside the sandbox
    script_lines = [
        "#!/bin/bash",
        "set -e",
        f"cd {workdir}",
        "git checkout .",  # Clean state
    ]
    
    if patch:
        # Write patch to file and apply it
        script_lines.extend([
            f"cat > /tmp/{instance_id}.diff << 'PATCH_EOF'",
            patch,
            "PATCH_EOF",
            f"git apply /tmp/{instance_id}.diff",
        ])
    
    # Run tests with markers
    script_lines.extend([
        f"echo \"+ : '{TEST_OUTPUT_START}'\"",
        f"{test_cmd} || true",  # Don't fail on test failures
        f"echo \"+ : '{TEST_OUTPUT_END}'\"",
    ])
    
    script = "\n".join(script_lines)
    
    try:
        # Create and run sandbox
        sb = modal.Sandbox.create(
            app=app,
            image=validator_image,
            timeout=timeout,
        )
        
        # Run the script
        process = sb.exec("bash", "-c", script)
        
        # Wait for completion and get output
        stdout = process.stdout.read()
        stderr = process.stderr.read()
        exit_code = process.wait()
        
        sb.terminate()
        
        return {
            "instance_id": instance_id,
            "output": stdout + stderr,
            "exit_code": exit_code,
        }
    except Exception as e:
        return {
            "instance_id": instance_id,
            "error": str(e),
        }


def spawn_generation_task(repo_name: str, max_bugs: int, interleave: bool):
    """
    Spawn a generation task without blocking (returns a FunctionCall handle).
    Returns (repo_name, repo_id, handle) or (repo_name, None, error_dict) on failure.
    """
    try:
        profile = resolve_profile(repo_name)
        repo_id = profile.repo_name
        print(f"Spawning generation for {repo_name} (profile: {profile.__class__.__name__})...")
        
        # spawn() returns immediately with a FunctionCall handle
        handle = generate_bugs_remote.spawn(
            repo_name=repo_name,
            max_bugs=max_bugs,
            interleave=interleave
        )
        return (repo_name, repo_id, handle)
    except Exception as e:
        return (repo_name, None, {"repo": repo_name, "error": f"Failed to resolve profile: {e}"})


def process_generation_result(repo_name: str, repo_id: str, results: dict) -> dict:
    """
    Process the results from a completed generation task.
    """
    if "error" in results:
        print(f"Error during bug generation for {repo_name}:")
        print(results["error"])
        if "traceback" in results:
            print(results["traceback"])
        return {"repo": repo_name, "repo_id": repo_id, "error": results["error"]}
    
    # Parse result patches
    if "patches_json" not in results:
        print(f"Warning: No patches_json returned for {repo_name}")
        if "bug_gen_zip" in results:
            print("Saving bug_gen_zip for manual inspection...")
            local_bug_dir = Path(f"logs/bug_gen/{repo_id}")
            local_bug_dir.mkdir(parents=True, exist_ok=True)
            zip_path = local_bug_dir / "bugs.zip"
            with open(zip_path, "wb") as f:
                f.write(results["bug_gen_zip"])
            subprocess.run(["unzip", "-o", str(zip_path), "-d", str(local_bug_dir)], check=True)
            print(f"Bugs extracted to {local_bug_dir}")
        return {"repo": repo_name, "repo_id": repo_id, "error": "No patches_json returned"}
    
    patches = json.loads(results["patches_json"])
    if not patches:
        print(f"No bugs were generated for {repo_name}.")
        return {"repo": repo_name, "repo_id": repo_id, "patches": [], "total_bugs": 0}
    
    # Save artifacts locally
    local_bug_dir = Path(f"logs/bug_gen/{repo_id}")
    local_bug_dir.mkdir(parents=True, exist_ok=True)
    
    with open(local_bug_dir.parent / f"{repo_id}_all_patches.json", "w") as f:
        f.write(results["patches_json"])
    
    if "bug_gen_zip" in results:
        zip_path = local_bug_dir / "bugs.zip"
        with open(zip_path, "wb") as f:
            f.write(results["bug_gen_zip"])
        subprocess.run(["unzip", "-o", str(zip_path), "-d", str(local_bug_dir)], check=True)
        os.remove(zip_path)
    
    print(f"Generated {len(patches)} bugs for {repo_name}")
    return {
        "repo": repo_name,
        "repo_id": repo_id,
        "patches": patches,
        "total_bugs": len(patches)
    }


def process_single_repo_validation(repo_name: str, repo_id: str, patches: list, profile, modal_app: modal.App) -> dict:
    """
    Process validation for a single repo (within app.run() context).
    Returns validation results dict.
    """
    print(f"\n{'='*60}")
    print(f"Validating {len(patches)} bugs for: {repo_name}")
    print(f"{'='*60}")
    
    from swesmith.constants import ENV_NAME
    test_cmd = profile.test_cmd
    workdir = f"/{ENV_NAME}"
    
    print(f"Test command: {test_cmd}")
    print(f"Workdir: {workdir}")
    print(f"Using image: {profile.image_name}")
    
    # 1. Run Baseline (Pre-gold)
    baseline_id = f"{repo_id}.ref"
    print(f"Running baseline (pre-gold) test suite for {baseline_id}...")
    
    baseline = run_validation_in_sandbox(
        app=modal_app,
        image_name=profile.image_name,
        instance_id=baseline_id,
        test_cmd=test_cmd,
        workdir=workdir,
        patch=None,
        timeout=profile.timeout_ref
    )
    
    if "error" in baseline:
        print(f"Baseline failed for {repo_name}: {baseline['error']}")
        return {"repo": repo_name, "error": f"Baseline failed: {baseline['error']}"}
    
    # Save baseline results
    valid_results_dir = Path(f"logs/run_validation/{repo_id}")
    valid_results_dir.mkdir(parents=True, exist_ok=True)
    
    baseline_dir = valid_results_dir / baseline_id
    baseline_dir.mkdir(parents=True, exist_ok=True)
    
    baseline_log_path = baseline_dir / "test_output.txt"
    with open(baseline_log_path, "w") as f:
        f.write(baseline["output"])
    
    # 2. Run post-gold for all patches in parallel
    # Using ThreadPoolExecutor to run multiple Sandboxes concurrently
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    print(f"Running post-gold tests in parallel for {len(patches)} patches...")
    
    def run_patch_validation(patch_info):
        idx, p = patch_info
        return run_validation_in_sandbox(
            app=modal_app,
            image_name=profile.image_name,
            instance_id=p["instance_id"],
            test_cmd=test_cmd,
            workdir=workdir,
            patch=p["patch"],
            timeout=profile.timeout
        )
    
    val_results = [None] * len(patches)
    max_workers = 100  # Limit concurrent sandboxes
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_idx = {
            executor.submit(run_patch_validation, (i, p)): i 
            for i, p in enumerate(patches)
        }
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                val_results[idx] = future.result()
            except Exception as e:
                val_results[idx] = {"instance_id": patches[idx]["instance_id"], "error": str(e)}
            completed += 1
            if completed % 10 == 0 or completed == len(patches):
                print(f"  Progress: {completed}/{len(patches)} patches validated")
    
    # 3. Grade locally
    from swesmith.harness.grading import get_valid_report
    reports = []
    valid_bugs_count = 0
    
    for i, res in enumerate(val_results):
        if "error" in res:
            inst_id = patches[i].get("instance_id", f"patch_{i}")
            print(f"Validation error for {inst_id}: {res['error']}")
            continue
        
        inst_id = res["instance_id"]
        inst_log_dir = valid_results_dir / inst_id
        inst_log_dir.mkdir(parents=True, exist_ok=True)
        
        log_path = inst_log_dir / "test_output.txt"
        with open(log_path, "w") as f:
            f.write(res["output"])
        
        try:
            report = get_valid_report(
                val_pregold_path=str(baseline_log_path),
                val_postgold_path=str(log_path),
                instance=patches[i]
            )
            
            with open(inst_log_dir / "report.json", "w") as f:
                json.dump(report, f, indent=4)
            
            reports.append({
                "instance_id": inst_id,
                "report": report
            })
            
            if len(report.get("PASS_TO_FAIL", [])) > 0:
                valid_bugs_count += 1
        except Exception as e:
            print(f"Error grading {inst_id}: {e}")
    
    # Save validation summary
    with open(valid_results_dir / "validation_summary.json", "w") as f:
        json.dump(reports, f, indent=2)
    
    print(f"Validation complete for {repo_name}: {valid_bugs_count}/{len(patches)} valid bugs")
    return {
        "repo": repo_name,
        "total_bugs": len(patches),
        "valid_bugs": valid_bugs_count,
        "logs_dir": str(valid_results_dir)
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modal Bug Generation & Validation")
    parser.add_argument("--repos", nargs="*", default=None, help="Repository names (owner/repo). If not specified, runs on all repos for the language.")
    parser.add_argument("--language", required=True, help="Language (e.g. javascript, python, golang)")
    parser.add_argument("--max-bugs", type=int, default=100, help="Max bugs per modifier")
    parser.add_argument("--interleave", action="store_true", help="Interleave modifiers")
    parser.add_argument("--validate-only", action="store_true", help="Skip generation and only run validation using local logs")
    
    args = parser.parse_args()
    
    # Determine which repos to process
    if args.repos:
        repos_to_process = args.repos
    else:
        repos_to_process = get_repos_for_language(args.language)
        print(f"Found {len(repos_to_process)} repos for language '{args.language}':")
        for repo in repos_to_process:
            print(f"  - {repo}")
    
    if not repos_to_process:
        print(f"No repos found for language: {args.language}")
        exit(1)
    
    all_results = []
    
    # Single app.run() context for all repos - Modal handles parallelism on remote workers
    with app.run():
        if not args.validate_only:
            # Phase 1: Generate bugs for all repos IN PARALLEL
            print(f"\n{'#'*60}")
            print(f"# PHASE 1: BUG GENERATION ({len(repos_to_process)} repos) - PARALLEL")
            print(f"{'#'*60}")
            
            # Spawn all generation tasks at once (non-blocking)
            spawn_results = []
            for repo in repos_to_process:
                spawn_results.append(
                    spawn_generation_task(repo, args.max_bugs, args.interleave)
                )
            
            print(f"\nSpawned {len(spawn_results)} generation tasks. Waiting for results...")
            
            # Wait for all results and process them
            generation_results = []
            for repo_name, repo_id, handle_or_error in spawn_results:
                if isinstance(handle_or_error, dict):
                    # This was an error during spawn
                    generation_results.append(handle_or_error)
                else:
                    # This is a FunctionCall handle - wait for result
                    try:
                        results = handle_or_error.get()  # Blocks until this task completes
                        gen_result = process_generation_result(repo_name, repo_id, results)
                        generation_results.append(gen_result)
                    except Exception as e:
                        generation_results.append({
                            "repo": repo_name,
                            "repo_id": repo_id,
                            "error": f"Generation failed: {e}"
                        })
            
            # Phase 2: Validate bugs for each repo that succeeded
            print(f"\n{'#'*60}")
            print(f"# PHASE 2: VALIDATION")
            print(f"{'#'*60}")
            
            for gen_result in generation_results:
                if "error" in gen_result:
                    all_results.append(gen_result)
                    continue
                
                patches = gen_result.get("patches", [])
                if not patches:
                    all_results.append({
                        "repo": gen_result["repo"],
                        "total_bugs": 0,
                        "valid_bugs": 0
                    })
                    continue
                
                try:
                    profile = resolve_profile(gen_result["repo"])
                    val_result = process_single_repo_validation(
                        gen_result["repo"],
                        gen_result["repo_id"],
                        patches,
                        profile,
                        modal_app=app
                    )
                    all_results.append(val_result)
                except Exception as e:
                    all_results.append({
                        "repo": gen_result["repo"],
                        "error": f"Validation failed: {e}"
                    })
        else:
            # Validate-only mode
            print(f"\n{'#'*60}")
            print(f"# VALIDATION ONLY MODE")
            print(f"{'#'*60}")
            
            for repo in repos_to_process:
                try:
                    profile = resolve_profile(repo)
                    repo_id = profile.repo_name
                    
                    patches_file = Path(f"logs/bug_gen/{repo_id}_all_patches.json")
                    if not patches_file.exists():
                        all_results.append({
                            "repo": repo,
                            "error": f"Patches file {patches_file} not found"
                        })
                        continue
                    
                    with open(patches_file, "r") as f:
                        patches = json.load(f)
                    
                    if not patches:
                        all_results.append({
                            "repo": repo,
                            "total_bugs": 0,
                            "valid_bugs": 0
                        })
                        continue
                    
                    val_result = process_single_repo_validation(
                        repo, repo_id, patches, profile,
                        modal_app=app
                    )
                    all_results.append(val_result)
                except Exception as e:
                    all_results.append({
                        "repo": repo,
                        "error": f"Failed: {e}"
                    })
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    total_bugs = 0
    total_valid = 0
    errors = []
    
    for result in all_results:
        repo = result.get("repo", "unknown")
        if "error" in result:
            errors.append(f"{repo}: {result['error']}")
        else:
            bugs = result.get("total_bugs", 0)
            valid = result.get("valid_bugs", 0)
            total_bugs += bugs
            total_valid += valid
            print(f"{repo}: {valid}/{bugs} valid bugs")
    
    print(f"\nTotal: {total_valid}/{total_bugs} valid bugs across {len(repos_to_process)} repos")
    
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")
