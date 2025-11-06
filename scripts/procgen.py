#!/usr/bin/env python3
"""
Procedural Bug Generation for SWE-smith
Converts the procedural_bug_gen.sh script to Python
"""

import argparse
import inspect
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def run_command(cmd, shell=False, capture_output=False, check=True):
    """Run a shell command and handle errors."""
    try:
        if capture_output:
            result = subprocess.run(
                cmd, shell=shell, capture_output=True, text=True, check=check
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
            check=False,
        )
        container_ids = result.stdout.strip()

        if container_ids:
            subprocess.run(
                f"echo {container_ids} | xargs docker rm -f",
                shell=True,
                check=False,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        # Ignore cleanup errors
        pass


def check_docker_image(image_name):
    """Check if Docker image exists, pull if not."""
    print(f"[Step 1/4] Verifying Docker image...")

    # Check if image exists
    result = subprocess.run(
        ["docker", "image", "inspect", image_name], capture_output=True, check=False
    )

    if result.returncode == 0:
        print(f"✓ Docker image found: {image_name}")
        return True

    print(f"✗ Docker image not found: {image_name}")
    print("Attempting to pull the image...")

    try:
        subprocess.run(["docker", "pull", image_name], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print("Error: Failed to pull Docker image. Please ensure the image exists.")
        raise


def generate_bugs(repo_id, max_bugs):
    """Generate bugs procedurally."""
    print("\n[Step 2/4] Generating bugs procedurally...")
    print(
        f"Running: python -m swesmith.bug_gen.procedural.generate {repo_id} --max_bugs {max_bugs}"
    )

    try:
        subprocess.run(
            [
                "python",
                "-m",
                "swesmith.bug_gen.procedural.generate",
                repo_id,
                "--max_bugs",
                str(max_bugs),
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print("Error: Bug generation failed.")
        raise


def collect_patches(repo_id):
    """Collect all patches into a single file."""
    print("\n[Step 3/4] Collecting all patches...")
    patches_file = f"logs/bug_gen/{repo_id}_all_patches.json"
    print(f"Running: python -m swesmith.bug_gen.collect_patches logs/bug_gen/{repo_id}")

    try:
        subprocess.run(
            [
                "python",
                "-m",
                "swesmith.bug_gen.collect_patches",
                f"logs/bug_gen/{repo_id}",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print("Error: Patch collection failed.")
        raise

    # Verify patches file was created
    if Path(patches_file).exists():
        with open(patches_file, "r") as f:
            patches = json.load(f)
            num_patches = len(patches)
        print(f"✓ Collected {num_patches} patches to {patches_file}")
    else:
        print(f"✗ Patches file not found: {patches_file}")
        raise

    return patches_file


def get_num_cores():
    """Determine number of CPU cores for parallel validation."""
    try:
        if platform.system() == "Darwin":  # macOS
            result = subprocess.run(
                ["sysctl", "-n", "hw.ncpu"], capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        else:  # Linux
            result = subprocess.run(
                ["nproc"], capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
    except Exception:
        pass

    # Default to 8 if detection fails
    return 8


def run_validation(patches_file, num_cores, timeout_seconds, use_modal=False):
    """Run validation on generated patches with a configurable timeout.

    Args:
        patches_file: Path to patches JSON file
        num_cores: Number of cores for parallel validation (ignored if use_modal=True)
        timeout_seconds: Timeout in seconds for validation
        use_modal: If True, use Modal for massively parallel validation
    """
    print(f"\n[Step 4/4] Running validation...")
    
    if use_modal:
        print(f"Using Modal for massively parallel validation...")
        print(f"Running: modal run -m swesmith.harness.valid_modal --bug-patches {patches_file}")
        print(f"Using Image.from_registry() to load repo-specific Docker images...")
        print(f"This will run validation across many Modal sandboxes in parallel.")
        
        try:
            subprocess.run(
                [
                    "modal",
                    "run",
                    "-m",
                    "swesmith.harness.valid_modal",
                    "--bug-patches",
                    patches_file,
                ],
                check=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            print(f"\n⚠️  Warning: Modal validation timed out after {timeout_seconds} seconds.")
            print("Partial results may be available.")
        except subprocess.CalledProcessError:
            print("Warning: Modal validation encountered errors but may have partial results.")
    else:
        print(f"Running: python -m swesmith.harness.valid {patches_file} -w {num_cores}")
        print(f"Timeout: {timeout_seconds} seconds ({timeout_seconds / 60:.1f} minutes)")

        try:
            subprocess.run(
                [
                    "python",
                    "-m",
                    "swesmith.harness.valid",
                    patches_file,
                    "-w",
                    str(num_cores),
                ],
                check=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            print(f"\n⚠️  Warning: Validation timed out after {timeout_seconds} seconds.")
            print("Partial results may be available.")
        except subprocess.CalledProcessError:
            print("Warning: Validation encountered errors but may have partial results.")


def get_repos_for_language(language: str) -> List[Tuple[str, str, str]]:
    """Get all repositories for a given language.

    Args:
        language: Programming language (e.g., 'rust', 'python', 'go', 'golang',
                                       'c', 'cpp', 'csharp', 'java', 'javascript', 'php')

    Returns:
        List of tuples (owner, repo, commit)

    Raises:
        ValueError: If the language is not supported
        ImportError: If the language module cannot be imported
    """
    import importlib
    from swesmith.profiles.base import RepoProfile

    # Normalize language name
    language = language.lower()

    # Map common language aliases to module names
    language_module_map = {
        "go": "golang",
    }
    module_name = language_module_map.get(language, language)

    # Map language to base profile class name
    # Most follow the pattern: Language + "Profile"
    # Special cases: golang -> GoProfile, javascript -> JavaScriptProfile, csharp -> CSharpProfile
    language_class_map = {
        "c": "CProfile",
        "cpp": "CppProfile",
        "csharp": "CSharpProfile",
        "java": "JavaProfile",
        "javascript": "JavaScriptProfile",
        "php": "PhpProfile",
        "python": "PythonProfile",
        "golang": "GoProfile",
        "rust": "RustProfile",
    }

    if module_name not in language_class_map:
        supported = ", ".join(sorted(language_class_map.keys()))
        raise ValueError(
            f"Language '{language}' is not supported. Supported languages: {supported}"
        )

    base_class_name = language_class_map[module_name]

    try:
        # Dynamically import the language module
        lang_module = importlib.import_module(f"swesmith.profiles.{module_name}")
    except ImportError as e:
        raise ImportError(
            f"Failed to import language module 'swesmith.profiles.{module_name}': {e}"
        )

    # Get the base profile class for this language
    if not hasattr(lang_module, base_class_name):
        raise AttributeError(
            f"Module 'swesmith.profiles.{module_name}' does not have class '{base_class_name}'"
        )

    base_class = getattr(lang_module, base_class_name)

    # Extract all repository profiles (subclasses of the base class)
    repos = []
    for name, obj in inspect.getmembers(lang_module):
        if (
            inspect.isclass(obj)
            and issubclass(obj, base_class)
            and obj.__name__ != base_class_name  # Exclude the base class itself
            and issubclass(obj, RepoProfile)  # Ensure it's a RepoProfile
        ):
            # Instantiate to get the values
            try:
                instance = obj()
                repos.append((instance.owner, instance.repo, instance.commit[:8]))
            except Exception as e:
                print(f"Warning: Failed to instantiate {obj.__name__}: {e}")
                continue

    return repos


def print_summary(repo_id, patches_file):
    """Print completion summary."""
    print("\n" + "=" * 42)
    print("Bug Generation Complete!")
    print("=" * 42)
    print(f"Generated patches: {patches_file}")
    print(f"Validation results: logs/run_validation/{repo_id}/")
    print("\nNext steps:")
    print(f"  1. Review validation results in logs/run_validation/{repo_id}/")
    print(f"  2. Analyze bugs with: python scripts/analyze_procmod_bugs.py {repo_id}")
    print(
        f"  3. Collect validated instances: python -m swesmith.harness.gather logs/run_validation/{repo_id}"
    )
    print("=" * 42)


def process_repo(
    repo_owner: str,
    repo_name_only: str,
    repo_commit: str,
    max_bugs: int,
    validation_timeout: int,
    use_modal: bool = False,
):
    """Process a single repository through the bug generation pipeline.

    Args:
        repo_owner: Repository owner
        repo_name_only: Repository name
        repo_commit: Commit hash (short form)
        max_bugs: Maximum bugs per modifier
        validation_timeout: Timeout in seconds for validation step
        use_modal: If True, use Modal for massively parallel validation
    """
    repo_name = f"{repo_owner}/{repo_name_only}"
    repo_id = f"{repo_owner}__{repo_name_only}.{repo_commit}"
    docker_image = f"jyangballin/swesmith.x86_64.{repo_owner.lower()}_{1776}_{repo_name_only.lower()}.{repo_commit}"

    # Print header
    print("\n" + "=" * 42)
    print("Procedural Bug Generation for SWE-smith")
    print("=" * 42)
    print(f"Repository: {repo_name}")
    print(f"Repository ID: {repo_id}")
    print(f"Max bugs per modifier: {max_bugs}")
    print(f"Docker image: {docker_image}")
    if use_modal:
        print(f"Validation: Modal (massively parallel)")
    else:
        print(f"Validation: Local (ThreadPool)")
    print("=" * 42)
    print()

    # Execute pipeline
    if not use_modal:
        check_docker_image(docker_image)
    generate_bugs(repo_id, max_bugs)
    patches_file = collect_patches(repo_id)
    num_cores = get_num_cores()
    run_validation(patches_file, num_cores, validation_timeout, use_modal=use_modal)
    print_summary(repo_id, patches_file)


def main():
    parser = argparse.ArgumentParser(
        description="Procedural Bug Generation for SWE-smith"
    )
    parser.add_argument(
        "--language",
        "-l",
        default="rust",
        help="Programming language to process (default: rust)",
    )
    parser.add_argument(
        "--max-bugs",
        "-m",
        type=int,
        default=200,
        help="Maximum number of bugs per modifier (default: 200)",
    )
    parser.add_argument(
        "--repo", "-r", help="Process only a specific repository (format: owner/repo)"
    )
    parser.add_argument(
        "--validation-timeout",
        "-t",
        type=int,
        default=600,
        help="Timeout in seconds for validation step (default: 600)",
    )
    parser.add_argument(
        "--use-modal",
        action="store_true",
        help="Use Modal for massively parallel validation (requires Modal setup)",
    )

    args = parser.parse_args()

    # Set Docker host for macOS
    if platform.system() == "Darwin":
        home = os.path.expanduser("~")
        os.environ["DOCKER_HOST"] = f"unix://{home}/.docker/run/docker.sock"

    # Clean up stale containers
    cleanup_containers()

    # Get repositories to process
    if args.repo:
        # Single repository mode
        repos = get_repos_for_language(args.language)
        repo_owner, repo_name_only = args.repo.split("/")

        # Find matching repo with commit
        matching_repo = None
        for owner, repo, commit in repos:
            if owner == repo_owner and repo == repo_name_only:
                matching_repo = (owner, repo, commit)
                break

        if not matching_repo:
            print(
                f"Error: Repository {args.repo} not found in {args.language} profiles"
            )
            sys.exit(1)

        repos = [matching_repo]
    else:
        # All repositories mode
        repos = get_repos_for_language(args.language)

    # Print overall summary
    print("=" * 60)
    print(f"Processing {len(repos)} {args.language.upper()} repositories")
    print("=" * 60)
    for i, (owner, repo, commit) in enumerate(repos, 1):
        print(f"{i:2d}. {owner}/{repo} @ {commit}")
    print("=" * 60)

    # Process each repository
    for i, (repo_owner, repo_name_only, repo_commit) in enumerate(repos, 1):
        print(f"\n\n{'=' * 60}")
        print(f"Processing repository {i}/{len(repos)}: {repo_owner}/{repo_name_only}")
        print(f"{'=' * 60}")

        try:
            process_repo(
                repo_owner,
                repo_name_only,
                repo_commit,
                args.max_bugs,
                args.validation_timeout,
                use_modal=args.use_modal,
            )
        except Exception as e:
            print(f"\n⚠️  Error processing {repo_owner}/{repo_name_only}: {e}")
            print("Continuing to next repository...")
            continue

    # Final summary
    print("\n\n" + "=" * 60)
    print("All repositories processed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
