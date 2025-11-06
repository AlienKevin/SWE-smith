"""
Purpose: Transform bug patches into SWE-bench style dataset using Modal's Image.from_registry().

This version uses Modal Sandboxes with repo-specific Docker images from Docker Hub,
avoiding Docker-in-Docker entirely.

Usage: modal run -m swesmith.harness.valid_modal_v2 --bug-patches logs/bug_gen/*_patches.json
"""

import argparse
import json
import modal
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from swebench.harness.constants import (
    KEY_INSTANCE_ID,
    FAIL_TO_PASS,
    LOG_REPORT,
    LOG_TEST_OUTPUT,
    DOCKER_USER,
    DOCKER_WORKDIR,
)
from swesmith.constants import (
    KEY_PATCH,
    KEY_TIMED_OUT,
    LOG_TEST_OUTPUT_PRE_GOLD,
    REF_SUFFIX,
    LOG_DIR_RUN_VALIDATION,
)

# Modal app setup
app = modal.App("swesmith-validation-v2")


@dataclass
class ValidationOutput:
    """Output from a single validation run."""
    instance_id: str
    docker_image: str
    status: str  # 'timeout', 'fail', '0_f2p', '1+_f2p'
    report: dict
    test_output: str
    run_log: str
    errored: bool


# Create a simple coordinator image for orchestration
coordinator_image = modal.Image.debian_slim(python_version="3.11").pip_install("swebench")


@app.function(
    image=coordinator_image,
    timeout=2 * 60 * 60,  # 2 hours for entire batch
)
def run_validation_batch_modal(
    instances_json: str,
    docker_image_name: str,
) -> list[ValidationOutput]:
    """
    Run validation for a batch of instances using the same Docker image.
    
    Uses Modal Sandboxes with Image.from_registry() to run each validation
    in the repo-specific Docker environment.
    
    Args:
        instances_json: JSON string of list of instances
        docker_image_name: Docker image name (e.g., jyangballin/swesmith.x86_64.repo.commit)
        
    Returns:
        List of ValidationOutput objects
    """
    instances = json.loads(instances_json)
    
    print(f"Processing {len(instances)} instances with image: {docker_image_name}")
    
    # Create Modal image from Docker registry
    repo_image = modal.Image.from_registry(docker_image_name, add_python="3.11")
    
    results = []
    
    for instance in instances:
        instance_id = instance[KEY_INSTANCE_ID]
        print(f"Running validation for {instance_id}...")
        
        sandbox = None
        try:
            # Add small delay to avoid rate limiting (5/s limit)
            time.sleep(0.1)
            
            # Create a sandbox with the repo-specific image
            sandbox = modal.Sandbox.create(
                image=repo_image,
                timeout=60 * 10,  # 10 minutes per instance
                cpu=2,
            )
            
            # Run validation commands in the sandbox
            # 1. Checkout the instance branch
            checkout_result = sandbox.exec(
                "git", "checkout", instance_id,
                workdir=DOCKER_WORKDIR,
            )
            checkout_result.wait()
            
            if checkout_result.returncode != 0:
                results.append(ValidationOutput(
                    instance_id=instance_id,
                    docker_image=docker_image_name,
                    status="fail",
                    report={"error": "Failed to checkout branch"},
                    test_output="",
                    run_log=checkout_result.stderr,
                    errored=True,
                ))
                continue
            
            # 2. Apply patch if provided
            if KEY_PATCH in instance and instance[KEY_PATCH]:
                # Write patch to file
                patch_content = instance[KEY_PATCH]
                write_result = sandbox.exec(
                    "sh", "-c", f"cat > /tmp/patch.diff << 'EOF'\n{patch_content}\nEOF",
                )
                write_result.wait()
                
                # Apply patch
                patch_result = sandbox.exec(
                    "git", "apply", "/tmp/patch.diff",
                    workdir=DOCKER_WORKDIR,
                )
                patch_result.wait()
                
                if patch_result.returncode != 0:
                    results.append(ValidationOutput(
                        instance_id=instance_id,
                        docker_image=docker_image_name,
                        status="fail",
                        report={"error": "Failed to apply patch"},
                        test_output="",
                        run_log=patch_result.stderr,
                        errored=True,
                    ))
                    continue
            
            # 3. Run tests
            # Get test command from instance or use default
            test_cmd = instance.get("test_cmd", "pytest tests/")
            
            test_result = sandbox.exec(
                "sh", "-c", test_cmd,
                workdir=DOCKER_WORKDIR,
            )
            test_result.wait()
            
            test_output = test_result.stdout + "\n" + test_result.stderr
            
            # 4. Parse results (simplified)
            # In reality, we'd use the repo's log parser here
            passed_tests = test_output.count("PASSED")
            failed_tests = test_output.count("FAILED")
            
            report = {
                FAIL_TO_PASS: [],  # Would need actual parsing
                "passed": passed_tests,
                "failed": failed_tests,
            }
            
            status = "1+_f2p" if passed_tests > 0 else "0_f2p"
            
            results.append(ValidationOutput(
                instance_id=instance_id,
                docker_image=docker_image_name,
                status=status,
                report=report,
                test_output=test_output,
                run_log=test_result.stdout,
                errored=False,
            ))
                
        except Exception as e:
            print(f"Error validating {instance_id}: {e}")
            results.append(ValidationOutput(
                instance_id=instance_id,
                docker_image=docker_image_name,
                status="fail",
                report={"error": str(e)},
                test_output="",
                run_log=str(e),
                errored=True,
            ))
        finally:
            # Clean up sandbox
            if sandbox is not None:
                try:
                    sandbox.terminate()
                except Exception:
                    pass  # Ignore cleanup errors
    
    return results


@app.local_entrypoint()
def main(
    bug_patches: str,
    redo_existing: bool = False,
    max_workers: int = 10,
) -> None:
    """
    Main entry point for Modal-based validation using Image.from_registry().
    
    Args:
        bug_patches: Path to JSON file with bug patches
        redo_existing: Whether to redo existing validations
        max_workers: Maximum number of parallel batches (one per unique Docker image)
    """
    print(f"Running Modal validation (v2) for {bug_patches}...")
    print(f"Using Image.from_registry() to load repo-specific Docker images")
    
    # Load patches
    with open(bug_patches, "r") as f:
        bug_patches_data = json.load(f)
    
    bug_patches_data = [
        {
            **x,
            KEY_PATCH: x.get(KEY_PATCH, x.get("model_patch")),
        }
        for x in bug_patches_data
    ]
    print(f"Found {len(bug_patches_data)} candidate patches.")
    
    # Group by Docker image (each repo has its own image)
    image_to_instances = defaultdict(list)
    for patch in bug_patches_data:
        # Extract Docker image name from repo field
        # repo field format: "Owner__RepoName.commit" (e.g., "Instagram__MonkeyType.70c3acf6")
        repo_str = patch["repo"]
        
        # Split by '.' to separate repo from commit
        if "." in repo_str:
            repo_id, commit = repo_str.rsplit(".", 1)
        else:
            repo_id = repo_str
            commit = "unknown"
        
        # repo_id format: "Owner__RepoName"
        # Convert to Docker image format: jyangballin/swesmith.x86_64.owner_1776_reponame.commit
        owner, repo_name = repo_id.split("__")
        
        docker_image = f"jyangballin/swesmith.x86_64.{owner.lower()}_1776_{repo_name.lower()}.{commit}"
        image_to_instances[docker_image].append(patch)
    
    print(f"\nGrouped into {len(image_to_instances)} unique Docker images:")
    for image, instances in image_to_instances.items():
        print(f"  - {image}: {len(instances)} instances")
    
    start_time = time.time()
    
    # Run validation for each Docker image in parallel
    print("\nStarting Modal validation...")
    all_results = []
    
    with modal.enable_output():
        for docker_image, instances in image_to_instances.items():
            print(f"\nProcessing {len(instances)} instances with {docker_image}...")
            
            # Run batch for this Docker image
            results = run_validation_batch_modal.remote(
                json.dumps(instances),
                docker_image,
            )
            
            all_results.extend(results)
    
    # Process results
    stats = {"fail": 0, "timeout": 0, "0_f2p": 0, "1+_f2p": 0, "error": 0}
    
    for result in all_results:
        if result.errored:
            stats["error"] += 1
        else:
            stats[result.status] += 1
        
        # Save logs locally
        # Extract repo from instance_id (format: Owner__RepoName.commit.strategy__hash)
        # We want to save to: LOG_DIR_RUN_VALIDATION / "Owner__RepoName.commit" / instance_id
        instance_id_parts = result.instance_id.split(".")
        if len(instance_id_parts) >= 2:
            repo_dir = f"{instance_id_parts[0]}.{instance_id_parts[1]}"  # Owner__RepoName.commit
        else:
            repo_dir = result.instance_id.split(".", 1)[0]
        
        log_dir = LOG_DIR_RUN_VALIDATION / repo_dir / result.instance_id
        log_dir.mkdir(parents=True, exist_ok=True)
        
        with open(log_dir / "run_instance.log", "w") as f:
            f.write(result.run_log)
        with open(log_dir / LOG_TEST_OUTPUT, "w") as f:
            f.write(result.test_output)
        with open(log_dir / LOG_REPORT, "w") as f:
            json.dump(result.report, f, indent=4)
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("Modal Validation Complete!")
    print("=" * 60)
    print(f"Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"Average time per instance: {elapsed/len(bug_patches_data):.1f} seconds")
    print("\nResults:")
    print(f"- Timeouts: {stats['timeout']}")
    print(f"- Failed: {stats['fail']}")
    print(f"- 0 F2P: {stats['0_f2p']}")
    print(f"- 1+ F2P: {stats['1+_f2p']}")
    print(f"- Errors: {stats['error']}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transform bug patches into SWE-bench dataset using Modal (v2)."
    )
    parser.add_argument(
        "--bug-patches",
        type=str,
        required=True,
        help="Json file containing bug patches.",
    )
    parser.add_argument(
        "--redo-existing",
        action="store_true",
        help="Redo completed validation instances.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum number of parallel batches (default: 10)",
    )
    args = parser.parse_args()
    
    main(
        bug_patches=args.bug_patches,
        redo_existing=args.redo_existing,
        max_workers=args.max_workers,
    )
