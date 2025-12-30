"""
Modal Bug Generation & Validation Script
All logs are persisted to a Modal Volume.

Run with: modal run scripts/bug_gen.py [OPTIONS]
"""

import asyncio
import json
import logging
import shutil
import sys
from pathlib import Path

import modal
modal.enable_output()


# ============================================================================
# Asyncio Exception Logging (to diagnose 'socket.send() raised exception')
# ============================================================================

class DeduplicatingFilter(logging.Filter):
    """A logging filter that suppresses repeated log messages after a threshold."""
    
    def __init__(self, max_repeats: int = 5):
        super().__init__()
        self.max_repeats = max_repeats
        self._message_counts: dict[str, int] = {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Create a key from the log message (truncate to avoid memory issues)
        msg_key = f"{record.levelname}:{record.getMessage()[:100]}"
        
        self._message_counts[msg_key] = self._message_counts.get(msg_key, 0) + 1
        count = self._message_counts[msg_key]
        
        if count <= self.max_repeats:
            if count == self.max_repeats:
                # Modify the message to indicate suppression
                record.msg = f"{record.msg} (further repeats will be suppressed)"
            return True
        elif count % 1000 == 0:
            # Log summary every 1000 occurrences
            record.msg = f"[Repeated {count}x] {record.msg}"
            return True
        return False


def setup_asyncio_exception_logging():
    """
    Configure asyncio to limit duplicate log messages and capture exception details.
    
    The 'socket.send() raised exception' warning is logged by asyncio's 
    _SelectorSocketTransport.write() when an SSL/socket error occurs. This 
    adds a deduplication filter to prevent log spam.
    """
    # Get the asyncio logger and clear any existing handlers to avoid duplicates
    asyncio_logger = logging.getLogger('asyncio')
    
    # Remove existing handlers to prevent duplicate output
    asyncio_logger.handlers.clear()
    
    # Add a deduplicating filter
    dedup_filter = DeduplicatingFilter(max_repeats=5)
    
    # Set up a detailed formatter with the dedup filter
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]'
    ))
    handler.addFilter(dedup_filter)
    asyncio_logger.addHandler(handler)
    asyncio_logger.setLevel(logging.WARNING)  # Only warnings and above
    asyncio_logger.propagate = False  # Don't propagate to root logger (prevents duplicates)
    
    # Store exception counts to avoid log spam for unhandled exceptions
    _exception_counts: dict[str, int] = {}
    
    def custom_exception_handler(loop, context):
        """Custom exception handler that logs full exception details with deduplication."""
        exception = context.get('exception')
        message = context.get('message', 'Unknown async error')
        
        # Create a key for rate limiting
        exc_type = type(exception).__name__ if exception else 'Unknown'
        exc_key = f"{exc_type}:{message[:50]}"
        
        _exception_counts[exc_key] = _exception_counts.get(exc_key, 0) + 1
        count = _exception_counts[exc_key]
        
        # Only log full details for first 5 occurrences of each type
        if count <= 5:
            if exception:
                logging.error(
                    f"Asyncio exception #{count}: {message}\n"
                    f"  Exception type: {type(exception).__name__}\n"
                    f"  Exception: {exception}\n"
                    f"  Context: {context}"
                )
                if count == 5:
                    logging.warning(f"  (Further '{exc_key}' exceptions will be suppressed)")
            else:
                logging.error(f"Asyncio error #{count}: {message} | Context: {context}")
        elif count % 1000 == 0:
            # Log summary every 1000 occurrences
            logging.warning(f"Asyncio '{exc_key}' exception count: {count}")
    
    return custom_exception_handler

# ============================================================================
# Constants & Configuration
# ============================================================================

APP_NAME = "swesmith-bug-gen"
VOLUME_NAME = "swesmith-bug-gen"
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

REMOTE_VALIDATOR_SCRIPT = r"""
import sys
import json
import subprocess
import os
from pathlib import Path

# We need to make sure we can import these. 
# The image sets PYTHONPATH=/root, and swesmith is at /root/swesmith
if "/root" not in sys.path:
    sys.path.append("/root")

from swesmith.harness.grading import get_valid_report
from swesmith.constants import TEST_OUTPUT_START, TEST_OUTPUT_END

def main():
    try:
        config_path = sys.argv[1]
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        test_cmd = config['test_cmd']
        output_path = Path(config['output_path'])
        baseline_path = Path(config['baseline_path'])
        report_path = Path(config['report_path'])
        instance = config['instance']
        
        # Ensure output directory exists (it's on a volume mount)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Run test command
        print(f"Executing test: {test_cmd}")
        
        full_cmd = f"set -uxo pipefail; : '{TEST_OUTPUT_START}'; {test_cmd} || true; : '{TEST_OUTPUT_END}'"
        
        # execution
        proc = subprocess.run(
            full_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            executable="/bin/bash"
        )
        
        output_bytes = proc.stdout
        exit_code = proc.returncode
        
        # Decode
        output_str = output_bytes.decode('utf-8', errors='replace')
        
        # Write output to volume
        output_path.write_text(output_str, encoding='utf-8')
        print(f"Saved output to {output_path}")
        
        result_summary = {
            "instance_id": instance.get("instance_id"),
            "valid": False,
            "error": None,
            "exit_code": exit_code
        }

        # Check baseline and validate
        if baseline_path.exists():
            print(f"Baseline found at {baseline_path}, validating...")
            try:
                report = get_valid_report(
                    val_pregold_path=str(baseline_path),
                    val_postgold_path=str(output_path),
                    instance=instance
                )
                
                report_path.write_text(json.dumps(report, indent=4))
                print(f"Saved report to {report_path}")
                
                if len(report.get("PASS_TO_FAIL", [])) > 0:
                    result_summary["valid"] = True
                    print("Validation SUCCESS: Found PASS_TO_FAIL")
                else:
                    print("Validation result: No PASS_TO_FAIL")
                    
            except Exception as e:
                print(f"Validation error: {e}")
                result_summary["error"] = f"Grading error: {str(e)}"
        else:
            print(f"Baseline NOT found at {baseline_path}")
            result_summary["error"] = "Baseline not found"
            
        # Output result as JSON marked with special tags
        print(f"\n<<RESULT_JSON>>{json.dumps(result_summary)}<<RESULT_JSON>>")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Fallback error result
        res = {"valid": False, "error": str(e)}
        print(f"\n<<RESULT_JSON>>{json.dumps(res)}<<RESULT_JSON>>")

if __name__ == "__main__":
    main()
"""

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

def get_validator_image(image_name: str) -> modal.Image:
    """Get or create a validator image for the given Docker image name."""
    print(f"DEBUG: get_validator_image called for {image_name}")
    return (
        modal.Image.from_registry(image_name, add_python="3.11")
        .pip_install_from_pyproject("pyproject.toml", optional_dependencies=["validate"])
        .env({"PYTHONPATH": "/root"})
        .add_local_dir("swesmith", remote_path="/root/swesmith")
    )


app = modal.App(APP_NAME)
# Use Volume v2 for better scalability (more files, concurrent writes, faster commits)
logs_volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True, version=2)
LOGS_MOUNT_PATH = "/logs"  # Where the volume is mounted in Modal containers


# ============================================================================
# Volume I/O Helpers
# ============================================================================

def volume_write_text(path: str, content: str) -> None:
    """Write text content to a path on the Modal Volume."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(content)
        temp_path = f.name
    # Upload after temp file is closed but still exists
    with logs_volume.batch_upload() as batch:
        batch.put_file(temp_path, path)
    # Delete only after upload completes
    Path(temp_path).unlink()


def volume_write_bytes(path: str, content: bytes) -> None:
    """Write binary content to a path on the Modal Volume."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.bin', delete=False) as f:
        f.write(content)
        temp_path = f.name
    # Upload after temp file is closed but still exists
    with logs_volume.batch_upload() as batch:
        batch.put_file(temp_path, path)
    # Delete only after upload completes
    Path(temp_path).unlink()


def volume_read_text(path: str) -> str | None:
    """Read text content from the Modal Volume. Returns None if file doesn't exist."""
    try:
        data = b"".join(logs_volume.read_file(path))
        return data.decode("utf-8")
    except Exception:
        return None


def volume_file_exists(path: str) -> bool:
    """Check if a file exists on the Modal Volume."""
    try:
        # Try to read a small portion - if it fails, file doesn't exist
        for _ in logs_volume.read_file(path):
            return True
        return True
    except Exception:
        return False


def volume_list_dir(path: str) -> list[str]:
    """List files/directories in a path on the Modal Volume."""
    try:
        entries = list(logs_volume.listdir(path))
        return [e.path for e in entries]
    except Exception:
        return []


# ============================================================================
# Remote Bug Generation
# ============================================================================

@app.function(
    image=generator_image,
    secrets=[modal.Secret.from_name("GITHUB_TOKEN")],
    timeout=MODAL_TIMEOUT,
    volumes={LOGS_MOUNT_PATH: logs_volume},  # Mount volume for direct writes
)
def generate_bugs_remote(
    repo_name: str, max_bugs: int, interleave: bool,
    max_entities: int, max_candidates: int, language: str,
    timeout_buffer_seconds: int = 60
) -> dict:
    """Generate bugs for a repository on a remote Modal worker.
    
    Results are saved directly to the Modal Volume, reducing data transfer.
    Returns only a lightweight summary.
    """
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
    
    # Volume paths for saving results
    volume_base = Path(LOGS_MOUNT_PATH)
    volume_bug_dir = volume_base / language / "bug_gen" / repo_id

    def _safe_execute(func, error_msg, *args, **kwargs):
        import traceback
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"{error_msg}: {e}")
            traceback.print_exc()
            return None

    def save_results_to_volume() -> dict:
        """Collect results and save directly to Modal Volume. Returns summary."""
        if not logs_base.exists():
            print(f"LOGS BASE MISSING: {logs_base}")
            return {"error": f"Logs directory {logs_base} does not exist."}

        generated_dirs = [d for d in logs_base.iterdir() if d.is_dir()]
        if not generated_dirs:
            print(f"NO DATA IN LOGS BASE. Files: {list(logs_base.glob('**/*'))}")
            return {"error": "No data generated"}

        repo_id_actual = sorted(generated_dirs, key=lambda x: x.stat().st_mtime, reverse=True)[0].name
        print(f"Detected repo_id_actual: {repo_id_actual}")

        _safe_execute(collect_patches_main, "Error in collect_patches_main", str(logs_base / repo_id_actual))

        # Ensure volume directory exists
        volume_bug_dir.mkdir(parents=True, exist_ok=True)

        # Create and save zip
        def _save_zip():
            shutil.make_archive(f"/tmp/{repo_id_actual}", 'zip', str(logs_base / repo_id_actual))
            zip_path = f"/tmp/{repo_id_actual}.zip"
            dest_path = volume_bug_dir / "bugs.zip"
            shutil.copy(zip_path, dest_path)
            print(f"Saved bugs.zip to volume: {dest_path}")
        _safe_execute(_save_zip, "Error saving zip to volume")

        # Read and save patches
        patches_file = logs_base / f"{repo_id_actual}_all_patches.json"
        if patches_file.exists():
            patches_json = patches_file.read_text()
            patches = json.loads(patches_json)
            
            # Save patches to volume
            patches_dest = volume_base / language / "bug_gen" / f"{repo_id}_all_patches.json"
            patches_dest.write_text(patches_json)
            print(f"Saved {len(patches)} patches to volume: {patches_dest}")
            
            if not patches:
                # Mark as done with 0 bugs
                (volume_bug_dir / "done.txt").write_text("Generation completed: 0 bugs generated")
                return {"total_bugs": 0, "patches": []}
            
            # Mark as done
            (volume_bug_dir / "done.txt").write_text(f"Generation completed: {len(patches)} bugs generated")
            logs_volume.commit()  # Force internal commit to persist done.txt immediately
            return {"total_bugs": len(patches), "patches": patches}
        else:
            print(f"Patches file not found. Available: {[p.name for p in logs_base.iterdir()]}")
            (volume_bug_dir / "error.txt").write_text("No patches_json generated")
            logs_volume.commit()
            return {"error": "No patches_json generated"}

    soft_timeout = MODAL_TIMEOUT - timeout_buffer_seconds
    print(f"Soft timeout: {soft_timeout}s")

    result = {"repo": repo_name, "repo_id": repo_id}
    
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
        print("\nCollecting and saving results to volume...")
        
        collection_result = _safe_execute(save_results_to_volume, "Error saving results")
        if collection_result:
            result.update(collection_result)
        else:
            result["error"] = "Failed to collect results"
        
        # Save log to volume
        log_content = log_buffer.getvalue()
        try:
            volume_bug_dir.mkdir(parents=True, exist_ok=True)
            (volume_bug_dir / "modal_output.log").write_text(log_content)
        except Exception as e:
            print(f"Failed to save log: {e}")
        
        # If there was an error, write error file
        if "error" in result:
            try:
                (volume_bug_dir / "error.txt").write_text(f"Bug generation failed: {result['error']}")
            except:
                pass
        
        # Commit volume changes
        logs_volume.commit()

    return result


# ============================================================================
# Validation Sandbox
# ============================================================================
async def run_validation_in_sandbox(
    semaphore: asyncio.Semaphore, app: modal.App, image_name: str, instance_id: str,
    test_cmd: str, workdir: str, patch: str | None, timeout: int,
    postgold_config: dict | None = None
) -> dict:
    """
    Run validation in a Modal Sandbox with a specific Docker image.
    
    If postgold_config is provided, runs the remote validator script and returns
    summary metadata. Results are written directly to the volume.
    
    If postgold_config is None, runs generic test cmd and returns output.
    """
    async with semaphore:
        print(f"[{instance_id}] Getting validator image ({image_name})...")
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
        
        # Prepare Sandbox arguments
        sandbox_kwargs = {
            "app": app,
            "image": validator_image,
            "timeout": timeout,
        }
        
        if postgold_config:
            # Mount logs volume for direct writing
            sandbox_kwargs["volumes"] = {LOGS_MOUNT_PATH: logs_volume}
            
            # Write config and validator script
            config_json = json.dumps(postgold_config)
            script_lines.extend([
                f"cat > /tmp/config.json << 'CONFIG_EOF'",
                config_json, "CONFIG_EOF",
                f"cat > /tmp/validator.py << 'SCRIPT_EOF'",
                REMOTE_VALIDATOR_SCRIPT, "SCRIPT_EOF",
                f"python3 /tmp/validator.py /tmp/config.json"
            ])
        else:
            # Legacy/Pregold mode: just run test
            script_lines.extend([
                f": '{TEST_OUTPUT_START}'",
                f"{test_cmd} || true",
                f": '{TEST_OUTPUT_END}'",
            ])
        
        try:
            # Use Modal's native async APIs
            print(f"[{instance_id}] Creating sandbox...")
            sb = await modal.Sandbox.create.aio(**sandbox_kwargs)
            
            print(f"[{instance_id}] Executing script...")
            process = await sb.exec.aio("bash", "-c", "\n".join(script_lines))
            
            try:
                print(f"[{instance_id}] Reading stdout...")
                output_raw = await process.stdout.read.aio()
            except UnicodeDecodeError as e:
                return {"instance_id": instance_id, "error": f"Binary output (decode failed at pos {e.start})"}
            
            print(f"[{instance_id}] Waiting for exit code...")
            exit_code = await process.wait.aio()
            
            print(f"[{instance_id}] Terminating sandbox...")
            await sb.terminate.aio()
            
            output = output_raw.decode("utf-8", errors="replace") if isinstance(output_raw, bytes) else output_raw
            print(f'{output=}')
            
            if postgold_config:
                # Parse JSON result from output
                if "<<RESULT_JSON>>" in output:
                    try:
                        json_str = output.split("<<RESULT_JSON>>")[1]
                        result = json.loads(json_str)
                        # Ensure error is propagated if script failed but printed JSON
                        if result.get("exit_code", 0) != 0 and not result.get("error"):
                            # This usually shouldn't happen with our script unless test failed (which is normal)
                             # But let's trust the 'valid' flag and 'error' field
                             pass
                        return result
                    except Exception as e:
                        return {"instance_id": instance_id, "error": f"Failed to parse remote result: {e}", "raw_output": output}
                else:
                     return {"instance_id": instance_id, "error": "No remote result found", "raw_output": output}
            else:
                return {"instance_id": instance_id, "output": output, "exit_code": exit_code}
                
        except UnicodeDecodeError as e:
            return {"instance_id": instance_id, "error": f"Binary output (decode failed at pos {e.start})"}
        except Exception as e:
            err_str = str(e)
            if "timeout" in err_str.lower() or "SandboxTimeoutError" in err_str:
                return {"instance_id": instance_id, "error": f"Timeout ({timeout}s)"}
            return {"instance_id": instance_id, "error": err_str}


# ============================================================================
# Generation Phase (using Modal .map() for true parallel processing)
# ============================================================================

def run_generation_phase(repos: list[str], args, language: str) -> list[dict]:
    """Run bug generation for all repos in parallel using Modal .map().
    
    Uses Modal's .map() for true parallel processing with autoscaling workers.
    Each worker saves results directly to the Volume, reducing data transfer.
    Returns lightweight summaries.
    """
    print(f"{'#'*60}")
    print(f"# PHASE 1: BUG GENERATION ({len(repos)} repos)")
    print(f"{'#'*60}\n")

    # Prepare inputs: resolve profiles and filter already-processed repos
    repo_inputs = []  # List of (repo_name, repo_id) tuples for repos to process
    skipped_done = 0
    skipped_error = 0
    failed_to_resolve = []  # Repos that failed profile resolution
    
    for repo in repos:
        try:
            profile = resolve_profile(repo)
            repo_id = profile.repo_name
        except Exception as e:
            failed_to_resolve.append({"repo": repo, "repo_id": None, "error": f"Failed to resolve profile: {e}"})
            continue
            
        volume_bug_dir = f"{language}/bug_gen/{repo_id}"
        
        # Check if already done or errored
        if volume_file_exists(f"{volume_bug_dir}/done.txt"):
            print(f"  Skipping {repo}: already completed")
            skipped_done += 1
        elif volume_file_exists(f"{volume_bug_dir}/error.txt"):
            print(f"  Skipping {repo}: previously failed")
            skipped_error += 1
        elif volume_file_exists(f"{language}/bug_gen/{repo_id}_all_patches.json"):
            print(f"  Skipping {repo}: patches already exist")
            skipped_done += 1
        else:
            repo_inputs.append((repo, repo_id))
    
    if skipped_done or skipped_error:
        print(f"\nSkipped {skipped_done} completed, {skipped_error} failed repos\n")
    
    if not repo_inputs and not failed_to_resolve:
        print("All repos already processed!\n")
        return []

    repo_names = [r[0] for r in repo_inputs]
    
    print(f"Running {len(repo_names)} generation tasks with Modal .map()...\n")
    
    # Use Modal .map() for true parallel processing with autoscaling
    # Each worker saves results directly to Volume; we just collect summaries
    generation_results = list(failed_to_resolve)  # Start with failed profile resolutions
    
    if repo_names:
        completed = 0
        total_bugs = 0
        
        for result_or_exc in generate_bugs_remote.map(
            repo_names,
            kwargs={
                "max_bugs": args.max_bugs,
                "interleave": args.interleave,
                "max_entities": args.max_entities,
                "max_candidates": args.max_candidates,
                "language": language,  # Workers save directly to Volume
            },
            return_exceptions=True,
        ):
            completed += 1
            
            if isinstance(result_or_exc, Exception):
                # Worker crashed - result already includes repo info from the exception context
                generation_results.append({"error": f"Worker exception: {result_or_exc}"})
                print(f"  [{completed}/{len(repo_names)}] ERROR: {result_or_exc}")
            else:
                # Result is a dict with repo, repo_id, total_bugs/patches/error
                generation_results.append(result_or_exc)
                repo = result_or_exc.get("repo", "unknown")
                if "error" in result_or_exc:
                    print(f"  [{completed}/{len(repo_names)}] {repo}: ERROR - {result_or_exc['error'][:50]}")
                else:
                    bugs = result_or_exc.get("total_bugs", 0)
                    total_bugs += bugs
                    print(f"  [{completed}/{len(repo_names)}] {repo}: {bugs} bugs generated")
        
        print(f"\nGeneration complete: {total_bugs} total bugs from {len(repo_names)} repos\n")

    return generation_results



# ============================================================================
# Validation Phase
# ============================================================================

def annotate_patches(patches: list, repo: str, repo_id: str, profile, language: str) -> list:
    """Add metadata to patches for validation."""
    for p in patches:
        p["_repo"] = repo
        p["_repo_id"] = repo_id
        p["_profile"] = profile
        p["_language"] = language
    return patches


def collect_patches_from_files(repos: list[str], language: str) -> list[dict]:
    """Collect patches from Modal Volume for validate-only mode."""
    import re
    all_patches = []
    
    for repo in repos:
        try:
            profile = resolve_profile(repo)
        except Exception:
            print(f"  Skipping {repo}: profile not found")
            continue

        repo_id = profile.repo_name
        
        # 1. Check if validation previously failed (broken baseline)
        if volume_file_exists(f"{language}/run_validation/{repo_id}/{repo_id}.ref/error.txt"):
            print(f"  Skipping {repo}: validation previously failed (pre-gold)")
            continue
            
        # 2. Check if generation failed
        bug_gen_dir = f"{language}/bug_gen/{repo_id}"
        if volume_file_exists(f"{bug_gen_dir}/error.txt"):
            print(f"  Skipping {repo}: bug generation failed")
            continue
            
        # 3. Check patch count from done.txt to avoid reading large files for small repos
        done_content = volume_read_text(f"{bug_gen_dir}/done.txt")
        if done_content:
            match = re.search(r"completed: (\d+) bugs", done_content)
            if match:
                count = int(match.group(1))
                if count < MIN_PATCHES_FOR_VALIDATION:
                    print(f"  Skipping {repo}: too few patches ({count} < {MIN_PATCHES_FOR_VALIDATION})")
                    continue
        
        # 4. Read patches
        patches_path = f"{language}/bug_gen/{repo_id}_all_patches.json"
        patches_json = volume_read_text(patches_path)
        
        if patches_json:
            patches = json.loads(patches_json)
            all_patches.extend(annotate_patches(patches, repo, repo_id, profile, language))
            print(f"  {repo}: {len(patches)} patches")
        else:
            print(f"  Skipping {repo}: no patches file")
    return all_patches


def collect_patches_from_generation(generation_results: list[dict], language: str) -> tuple[list[dict], list[dict]]:
    """Collect patches from generation results, separating errors."""
    all_patches, errors = [], []
    for gen_result in generation_results:
        if "error" in gen_result:
            errors.append(gen_result)
            continue
        patches = gen_result.get("patches", [])
        if patches:
            profile = resolve_profile(gen_result["repo"])
            all_patches.extend(annotate_patches(patches, gen_result["repo"], gen_result["repo_id"], profile, language))
    return all_patches, errors


def build_repos_with_patches(all_patches: list) -> dict:
    """Build repos_with_patches dict from annotated patches."""
    repos = {}
    for p in all_patches:
        repo = p["_repo"]
        if repo not in repos:
            repos[repo] = {"profile": p["_profile"], "repo_id": p["_repo_id"], "language": p["_language"]}
    return repos


async def run_pregold_phase_async(repos_with_patches: dict, max_concurrent: int, env_name: str) -> set[str]:
    """Run all pre-gold (baseline) tests asynchronously. Returns set of repos with 0 passing tests (to skip)."""
    import tempfile
    from swesmith.harness.grading import read_test_output
    from swebench.harness.constants import TestStatus
    
    print(f"\nPHASE: PRE-GOLD (BASELINE) TESTS")
    print(f"Running {len(repos_with_patches)} baselines, max concurrent: {max_concurrent}")
    
    tasks = []
    previously_failed = set()  # Repos that failed in previous runs
    
    for repo, info in repos_with_patches.items():
        lang = info["language"]
        baseline_output_path = f"{lang}/run_validation/{info['repo_id']}/{info['repo_id']}.ref/test_output.txt"
        error_path = f"{lang}/run_validation/{info['repo_id']}/{info['repo_id']}.ref/error.txt"
        test_output_exists = volume_file_exists(baseline_output_path)
        error_exists = volume_file_exists(error_path)
        
        if test_output_exists and not error_exists:
            print(f"  Skipping {repo}: baseline exists")
        elif error_exists:
            print(f"  Skipping {repo}: previously failed")
            previously_failed.add(repo)
        else:
            tasks.append({
                "repo": repo, "repo_id": info["repo_id"], "profile": info["profile"],
                "instance_id": f"{info['repo_id']}.ref", "workdir": f"/{env_name}",
                "language": lang
            })
    
    if not tasks:
        print("  All baselines already exist!\\n")
        return previously_failed  # Return previously failed repos to skip in post-gold
    
    # Semaphore controls max concurrent operations
    semaphore = asyncio.Semaphore(max_concurrent)
    failed_repos = previously_failed.copy()  # Start with previously failed repos
    
    # Install custom exception handler to log socket.send() exception details
    loop = asyncio.get_running_loop()
    exception_handler = setup_asyncio_exception_logging()
    loop.set_exception_handler(exception_handler)
    
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
        
        lang = task["language"]
        volume_baseline_dir = f"{lang}/run_validation/{task['repo_id']}/{task['instance_id']}"
        
        try:
            if "error" not in result:
                # Save output to volume
                volume_write_text(f"{volume_baseline_dir}/test_output.txt", result["output"])
                
                # Validate baseline has at least 1 passing test (use temp file for parsing)
                try:
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                        f.write(result["output"])
                        temp_path = f.name
                    test_output, found = read_test_output(temp_path)
                    Path(temp_path).unlink()
                    
                    if found and test_output:
                        status_map = task["profile"].log_parser(test_output)
                        passed = sum(1 for s in status_map.values() if s == TestStatus.PASSED.value)
                        if passed == 0:
                            status = f"⚠️ 0 tests passed (skipping post-gold)"
                            failed_repos.add(task["repo"])
                            volume_write_text(f"{volume_baseline_dir}/error.txt", "Pre-gold failed: 0 tests passed")
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
                        volume_write_text(f"{volume_baseline_dir}/error.txt", f"Pre-gold failed: {reason}")
                except Exception as e:
                    status = f"OK (parse check failed: {e})"
            else:
                status = f"ERROR: {result['error'][:50]}"
                failed_repos.add(task["repo"])
                volume_write_text(f"{volume_baseline_dir}/error.txt", f"Pre-gold sandbox error: {result['error']}")
        except Exception as e:
            status = f"EXCEPTION: {e}"
            failed_repos.add(task["repo"])
            try:
                volume_write_text(f"{volume_baseline_dir}/error.txt", f"Pre-gold exception: {e}")
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
        if not volume_file_exists(f"{p['_language']}/run_validation/{p['_repo_id']}/{p['instance_id']}/report.json")
    ]
    
    print(f"  {len(all_patches) - len(tasks)} already validated, {len(tasks)} remaining")
    
    if not tasks:
        print("  All patches already validated!")
        return []
    
    # Semaphore controls max concurrent operations
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Install custom exception handler to log socket.send() exception details
    loop = asyncio.get_running_loop()
    exception_handler = setup_asyncio_exception_logging()
    loop.set_exception_handler(exception_handler)
    
    async def process_single_task(task: dict) -> dict:
        """Process a single validation task."""
        lang = task["full_patch"]["_language"]
        repo_id = task["repo_id"]
        instance_id = task["instance_id"]
        
        # Strip internal keys (prefixed with _) that contain non-serializable objects like the profile
        serializable_patch = {k: v for k, v in task["full_patch"].items() if not k.startswith("_")}
        
        postgold_config = {
            "test_cmd": task["profile"].test_cmd,
            "output_path": f"/logs/{lang}/run_validation/{repo_id}/{instance_id}/test_output.txt",
            "baseline_path": f"/logs/{lang}/run_validation/{repo_id}/{repo_id}.ref/test_output.txt",
            "report_path": f"/logs/{lang}/run_validation/{repo_id}/{instance_id}/report.json",
            "instance": serializable_patch
        }
        
        result = await run_validation_in_sandbox(
            semaphore=semaphore, app=app,
            image_name=task["profile"].image_name, instance_id=task["instance_id"],
            test_cmd=task["profile"].test_cmd, workdir=task["workdir"],
            patch=task["patch"], timeout=task["profile"].timeout,
            postgold_config=postgold_config
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
        
        processed = result
        processed["repo"] = task["repo"]
        # result already has instance_id, valid, error keys from the sandbox return
        
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

@app.local_entrypoint()
def main(
    repos: str = "",
    language: str = "javascript",
    max_bugs: int = 200,
    interleave: bool = False,
    max_entities: int = 2000,
    max_candidates: int = 2000,
    max_concurrent_tests: int = 900,
):
    """
    Modal Bug Generation & Validation script.
    
    Runs two phases:
    1. Generation: Creates bugs for repos (skips repos that are already done/failed)
    2. Validation: Validates all patches from the volume
    
    Run with: modal run scripts/bug_gen.py [OPTIONS]
    
    Arguments:
        repos: Comma-separated repository names (owner/repo), or empty to use all for language
        language: Language to process (default: javascript)
        max_bugs: Max bugs per modifier (default: 200)
        interleave: Interleave modifiers (default: False)
        max_entities: Max entities to sample, -1 for all (default: 2000)
        max_candidates: Max candidates to process, -1 for all (default: 2000)
        max_concurrent_tests: Max concurrent tests (default: 900)
    """
    from swesmith.constants import ENV_NAME
    
    # Parse repos (comma-separated string to list)
    repo_list = [r.strip() for r in repos.split(",") if r.strip()] if repos else []
    
    # Determine repos
    if repo_list:
        target_repos = repo_list
    else:
        target_repos = get_repos_for_language(language)
        
        # Skip problematic repos
        ignored_map = ["mrdoob/three.js", "riot/riot"]
        target_repos = [r for r in target_repos if r not in ignored_map]
        
        print(f"Found {len(target_repos)} repos for '{language}':")
        for r in target_repos:
            print(f"  - {r}")
    
    if not target_repos:
        print(f"No repos found for language: {language}")
        return
    
    print(f"\n{'='*60}")
    print(f"BUG GEN - {len(target_repos)} repos, {max_concurrent_tests} max concurrent")
    print(f"Volume: {VOLUME_NAME}/{language}/")
    print(f"{'='*60}\n")
    
    # Create a simple args-like object for compatibility
    class Args:
        pass
    args = Args()
    args.max_bugs = max_bugs
    args.interleave = interleave
    args.max_entities = max_entities
    args.max_candidates = max_candidates
    
    # Phase 1: Generation (skips repos that are already done/failed)
    generation_results = run_generation_phase(target_repos, args, language)
    
    # Phase 2: Validation - collect ALL patches from volume (not just from this run)
    print(f"\n{'#'*60}")
    print(f"# PHASE 2: VALIDATION")
    print(f"{'#'*60}\n")
    
    print("Collecting patches from volume...")
    all_patches = collect_patches_from_files(target_repos, language)
    print(f"Total: {len(all_patches)} patches\n")
    
    results = run_validation_phase(all_patches, max_concurrent_tests, ENV_NAME)
    
    if results:
        print_summary(results, len(build_repos_with_patches(all_patches)))
    
    # Report generation errors from this run
    errors = [r for r in generation_results if "error" in r]
    if errors:
        print(f"\nGeneration Errors ({len(errors)}):")
        for err in errors:
            print(f"  - {err['repo']}: {err.get('error', 'Unknown')}")
