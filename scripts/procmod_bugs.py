#!/usr/bin/env python3
"""
Procedural Bug Generation for SWE-smith
Converts the procedural_bug_gen.sh script to Python
"""

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def run_command(cmd, shell=False, capture_output=False, check=True):
    """Run a shell command and handle errors."""
    try:
        if capture_output:
            result = subprocess.run(
                cmd,
                shell=shell,
                capture_output=True,
                text=True,
                check=check
            )
            return result
        else:
            subprocess.run(cmd, shell=shell, check=check)
            return None
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e


def cleanup_containers():
    """Clean up stale containers from previous run."""
    try:
        # Get container IDs that match swesmith.val
        result = subprocess.run(
            "docker ps -a | grep swesmith.val | awk '{print $1}'",
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        container_ids = result.stdout.strip()
        
        if container_ids:
            subprocess.run(
                f"echo {container_ids} | xargs docker rm -f",
                shell=True,
                check=False,
                stderr=subprocess.DEVNULL
            )
    except Exception:
        # Ignore cleanup errors
        pass


def check_docker_image(image_name):
    """Check if Docker image exists, pull if not."""
    print(f"[Step 1/4] Verifying Docker image...")
    
    # Check if image exists
    result = subprocess.run(
        ["docker", "image", "inspect", image_name],
        capture_output=True,
        check=False
    )
    
    if result.returncode == 0:
        print(f"✓ Docker image found: {image_name}")
        return True
    
    print(f"✗ Docker image not found: {image_name}")
    print("Attempting to pull the image...")
    
    try:
        subprocess.run(["docker", "pull", image_name], check=True)
        return True
    except subprocess.CalledProcessError:
        print("Error: Failed to pull Docker image. Please ensure the image exists.")
        sys.exit(1)


def generate_bugs(repo_id, max_bugs):
    """Generate bugs procedurally."""
    print("\n[Step 2/4] Generating bugs procedurally...")
    print(f"Running: python -m swesmith.bug_gen.procedural.generate {repo_id} --max_bugs {max_bugs}")
    
    try:
        subprocess.run(
            ["python", "-m", "swesmith.bug_gen.procedural.generate", repo_id, "--max_bugs", str(max_bugs)],
            check=True
        )
    except subprocess.CalledProcessError:
        print("Error: Bug generation failed.")
        sys.exit(1)


def collect_patches(repo_id):
    """Collect all patches into a single file."""
    print("\n[Step 3/4] Collecting all patches...")
    patches_file = f"logs/bug_gen/{repo_id}_all_patches.json"
    print(f"Running: python -m swesmith.bug_gen.collect_patches logs/bug_gen/{repo_id}")
    
    try:
        subprocess.run(
            ["python", "-m", "swesmith.bug_gen.collect_patches", f"logs/bug_gen/{repo_id}"],
            check=True
        )
    except subprocess.CalledProcessError:
        print("Error: Patch collection failed.")
        sys.exit(1)
    
    # Verify patches file was created
    if Path(patches_file).exists():
        with open(patches_file, 'r') as f:
            patches = json.load(f)
            num_patches = len(patches)
        print(f"✓ Collected {num_patches} patches to {patches_file}")
    else:
        print(f"✗ Patches file not found: {patches_file}")
        sys.exit(1)
    
    return patches_file


def get_num_cores():
    """Determine number of CPU cores for parallel validation."""
    try:
        if platform.system() == "Darwin":  # macOS
            result = subprocess.run(
                ["sysctl", "-n", "hw.ncpu"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        else:  # Linux
            result = subprocess.run(
                ["nproc"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
    except Exception:
        pass
    
    # Default to 8 if detection fails
    return 8


def run_validation(patches_file, num_cores):
    """Run validation on generated patches."""
    print(f"\n[Step 4/4] Running validation...")
    print(f"Running: python -m swesmith.harness.valid {patches_file} -w {num_cores}")
    
    try:
        subprocess.run(
            ["python", "-m", "swesmith.harness.valid", patches_file, "-w", str(num_cores)],
            check=True
        )
    except subprocess.CalledProcessError:
        print("Warning: Validation encountered errors but may have partial results.")


def print_summary(repo_id, patches_file):
    """Print completion summary."""
    print("\n" + "=" * 42)
    print("Bug Generation Complete!")
    print("=" * 42)
    print(f"Generated patches: {patches_file}")
    print(f"Validation results: logs/run_validation/{repo_id}/")
    print("\nNext steps:")
    print(f"  1. Review validation results in logs/run_validation/{repo_id}/")
    print(f"  2. Analyze bugs with: python scripts/analyze_bugs.py {repo_id}")
    print(f"  3. Collect validated instances: python -m swesmith.harness.gather logs/run_validation/{repo_id}")
    print("=" * 42)


def main():
    parser = argparse.ArgumentParser(
        description="Procedural Bug Generation for SWE-smith"
    )
    parser.add_argument(
        "repo_name",
        nargs="?",
        default="dtolnay/anyhow",
        help="Repository name in format owner/repo (default: dtolnay/anyhow)"
    )
    parser.add_argument(
        "max_bugs",
        nargs="?",
        type=int,
        default=-1,
        help="Maximum number of bugs per modifier (default: -1 for unlimited)"
    )
    
    args = parser.parse_args()
    
    # Configuration
    repo_name = args.repo_name
    max_bugs = args.max_bugs
    repo_commit = "1d7ef1db"
    
    # Parse repository name
    repo_owner, repo_name_only = repo_name.split('/')
    repo_id = f"{repo_owner}__{repo_name_only}.{repo_commit}"
    docker_image = f"jyangballin/swesmith.x86_64.{repo_owner}_{1776}_{repo_name_only}.{repo_commit}"
    
    # Set Docker host for macOS
    if platform.system() == "Darwin":
        home = os.path.expanduser("~")
        os.environ["DOCKER_HOST"] = f"unix://{home}/.docker/run/docker.sock"
    
    # Print header
    print("=" * 42)
    print("Procedural Bug Generation for SWE-smith")
    print("=" * 42)
    print(f"Repository: {repo_name}")
    print(f"Repository ID: {repo_id}")
    print(f"Max bugs per modifier: {max_bugs}")
    print(f"Docker image: {docker_image}")
    print("=" * 42)
    print()
    
    # Clean up stale containers
    cleanup_containers()
    
    # Execute pipeline
    check_docker_image(docker_image)
    generate_bugs(repo_id, max_bugs)
    patches_file = collect_patches(repo_id)
    num_cores = get_num_cores()
    run_validation(patches_file, num_cores)
    print_summary(repo_id, patches_file)


if __name__ == "__main__":
    main()
