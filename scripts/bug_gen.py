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

# We need to parse enough args to determine the repo profile BEFORE defining the Modal app
# so we can set up the dynamic validator image.
def get_initial_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--repo", required=False)
    try:
        args, _ = parser.parse_known_args()
        return args
    except:
        return argparse.Namespace(repo=None)

# ... (the rest of the top-level stays similar but I'll update the generator_image too)

try:
    initial_args = get_initial_args()
    repo_name = initial_args.repo
    
    # If repo is None (remote import), use placeholder - the image is already built
    if repo_name is None:
        TARGET_IMAGE_NAME = "placeholder:latest"  # Won't be used, image already cached
        profile = None
    else:
        from swesmith.profiles import registry
        
        # Robust profile lookup (same logic as ensure_mirror)
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
        
        TARGET_IMAGE_NAME = profile.image_name
except Exception as e:
    raise RuntimeError(f"Failed to find profile for repo: {e}")

# Generator Image: For procedural generation
generator_image = (
    modal.Image.from_registry("ubuntu:22.04", add_python="3.11")
    .apt_install("git")
    .pip_install_from_pyproject("pyproject.toml")
    .env({"PYTHONPATH": "/root"})
    .add_local_dir("swesmith", remote_path="/root/swesmith")
    .add_local_file(".env", remote_path="/root/.env")
)

# Validator Image: The actual repo image from Docker Hub
# Modal requires Python, and module-level imports need swesmith
# Use minimal 'validate' dependency group to avoid heavy packages like sglang
print(f"TARGET_IMAGE_NAME: {TARGET_IMAGE_NAME}")
validator_image = (
    modal.Image.from_registry(TARGET_IMAGE_NAME, add_python="3.11")
    .pip_install_from_pyproject("pyproject.toml", optional_dependencies=["validate"])
    .env({"PYTHONPATH": "/root"})
    .add_local_dir("swesmith", remote_path="/root/swesmith")
)

app = modal.App(APP_NAME)


@app.function(
    image=generator_image,
    secrets=[modal.Secret.from_name("GITHUB_TOKEN")],
    timeout=60 * MINUTES,
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


@app.function(
    image=validator_image,
    timeout=30 * MINUTES,
)
def run_validation_remote(
    instance_id: str,
    test_cmd: str,
    workdir: str,
    patch: str | None = None,
    timeout: int = 300,
) -> dict:
    """
    Runs tests inside the validator image (minimal deps, no swesmith).
    If patch is None, runs pre-gold (baseline).
    All parameters are passed explicitly to avoid swesmith dependency.
    """
    import subprocess
    import os
    
    # Ensure workdir exists
    if not os.path.exists(workdir):
        return {"error": f"Workdir {workdir} does not exist", "instance_id": instance_id}
        
    # Ensure clean state (case of worker reuse)
    subprocess.run(["git", "checkout", "."], cwd=workdir, capture_output=True)

    # Apply patch if provided
    if patch:
        patch_path = f"/tmp/{instance_id}.diff"
        with open(patch_path, "w") as f:
            f.write(patch)
        try:
            subprocess.run(["git", "apply", patch_path], cwd=workdir, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            return {"error": f"Failed to apply patch: {e.stderr.decode()}", "instance_id": instance_id}

    # Run tests and capture markers
    full_cmd = f"cd {workdir} && echo \"+ : '{TEST_OUTPUT_START}'\" && {test_cmd} ; echo \"+ : '{TEST_OUTPUT_END}'\""
    
    try:
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        output = result.stdout + result.stderr
        exit_code = result.returncode
    except subprocess.TimeoutExpired as e:
        output = (e.stdout.decode() if e.stdout else "") + (e.stderr.decode() if e.stderr else "") + f"\n\nERROR: Tests timed out after {timeout} seconds"
        exit_code = 124
    
    return {
        "instance_id": instance_id,
        "output": output,
        "exit_code": exit_code
    }



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modal Bug Generation & Validation")
    parser.add_argument("--repo", required=True, help="Repository name (owner/repo)")
    parser.add_argument("--language", required=True, help="Language (e.g. javascript)")
    parser.add_argument("--max-bugs", type=int, default=200, help="Max bugs per modifier")
    parser.add_argument("--interleave", action="store_true", help="Interleave modifiers")
    parser.add_argument("--validate-only", action="store_true", help="Skip generation and only run validation using local logs")
    
    args = parser.parse_args()
    
    # Use the profile already resolved at module level (assumes mirror exists)
    print(f"Using profile: {profile.__class__.__name__}")
    repo_id = profile.repo_name  # Standard repo_id from profile
    
    results = None
    patches = None
    
    with app.run():
        if not args.validate_only:
            print(f"Submitting bug generation task for {args.repo}...")
            results = generate_bugs_remote.remote(
                repo_name=args.repo,
                max_bugs=args.max_bugs,
                interleave=args.interleave
            )
        
            if "error" in results:
                print("Error during bug generation:")
                print(results["error"])
                if "traceback" in results:
                    print(results["traceback"])
                exit(1)
                
            # Parse result patches
            if "patches_json" not in results:
                print("Warning: No patches_json returned from remote task.")
                # Check if we got a zip but no json (unlikely but possible if collection failed)
                if "bug_gen_zip" in results:
                    print("However, a bug_gen_zip was returned. Unpacking for manual inspection...")
                    local_bug_dir = Path(f"logs/bug_gen/{repo_id}")
                    local_bug_dir.mkdir(parents=True, exist_ok=True)
                    zip_path = local_bug_dir / "bugs.zip"
                    with open(zip_path, "wb") as f:
                        f.write(results["bug_gen_zip"])
                    subprocess.run(["unzip", "-o", str(zip_path), "-d", str(local_bug_dir)], check=True)
                    print(f"Bugs extracted to {local_bug_dir}")
                exit(1)

            patches = json.loads(results["patches_json"])
            if not patches:
                print("No bugs were generated.")
                exit(0)
                
            # Save artifacts Locally
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
        else:
            # Validate-only mode: load patches from local file
            print(f"Validation-only mode. Loading patches from logs/bug_gen/{repo_id}_all_patches.json...")
            patches_file = Path(f"logs/bug_gen/{repo_id}_all_patches.json")
            if not patches_file.exists():
                print(f"Error: Patches file {patches_file} not found. Cannot run validation-only.")
                exit(1)
            with open(patches_file, "r") as f:
                patches = json.load(f)
            
            local_bug_dir = Path(f"logs/bug_gen/{repo_id}")
            if not local_bug_dir.exists():
                print(f"Warning: Local bug directory {local_bug_dir} missing. Baseline might still work but post-gold logs won't be saved correctly if folder creation fails.")

        # Always run Validation (unless explicitly skipped via code flow)
        if patches:
            print(f"\nStarting remote validation for {len(patches)} bugs...")
            
            # Get test command and workdir from local profile
            from swesmith.constants import ENV_NAME
            test_cmd = profile.test_cmd  # Use base test command directly
            workdir = f"/{ENV_NAME}"
            
            print(f"Test command: {test_cmd}")
            print(f"Workdir: {workdir}")
            
            # 1. Run Baseline (Pre-gold)
            # swesmith conventions use f"{repo}.ref" for baseline data
            baseline_id = f"{repo_id}.ref"
            print(f"Running baseline (pre-gold) test suite for {baseline_id}...")
            
            baseline = run_validation_remote.remote(
                instance_id=baseline_id,
                test_cmd=test_cmd,
                workdir=workdir,
                patch=None,
                timeout=profile.timeout_ref
            )
            
            if "error" in baseline:
                print(f"Baseline failed: {baseline['error']}")
                exit(1)
            
            # Match swesmith folder structure
            valid_results_dir = Path(f"logs/run_validation/{repo_id}")
            valid_results_dir.mkdir(parents=True, exist_ok=True)
            
            baseline_dir = valid_results_dir / baseline_id
            baseline_dir.mkdir(parents=True, exist_ok=True)
            
            baseline_log_path = baseline_dir / "test_output.txt"
            with open(baseline_log_path, "w") as f:
                f.write(baseline["output"])
            
            # 2. Run post-gold for all patches in parallel
            print("Running post-gold tests in parallel...")
            
            # Build args for starmap - each tuple is (instance_id, test_cmd, workdir, patch, timeout)
            val_args = [
                (p["instance_id"], test_cmd, workdir, p["patch"], profile.timeout)
                for p in patches
            ]
            val_results = list(run_validation_remote.starmap(val_args))
            
            # 3. Grade locally using swe-smith grading logic
            from swesmith.harness.grading import get_valid_report
            reports = []
            valid_bugs_count = 0
            
            for i, res in enumerate(val_results):
                # Check for validation errors (e.g., patch application failure)
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
                    
                # Compute report
                try:
                    report = get_valid_report(
                        val_pregold_path=str(baseline_log_path),
                        val_postgold_path=str(log_path),
                        instance=patches[i]
                    )
                    
                    # Save individual report.json to match swe-smith structure
                    with open(inst_log_dir / "report.json", "w") as f:
                        json.dump(report, f, indent=4)
                        
                    reports.append({
                        "instance_id": inst_id,
                        "report": report
                    })
                    
                    # A bug is valid if it causes tests to fail (PASS in clean, FAIL with bug)
                    if len(report.get("PASS_TO_FAIL", [])) > 0:
                        valid_bugs_count += 1
                except Exception as e:
                    print(f"Error grading {inst_id}: {e}")
            
            # Save final validation summary
            with open(valid_results_dir / "validation_summary.json", "w") as f:
                json.dump(reports, f, indent=2)
                
            print(f"\nValidation Complete!")
            print(f"Total Bugs Created: {len(patches)}")
            print(f"Valid Bugs (P2F > 0): {valid_bugs_count}")
            print(f"Detailed logs at: {valid_results_dir}")
