import argparse
import os
import shutil
import json
import subprocess
from pathlib import Path

import modal

# Constants
APP_NAME = "swesmith-bug-gen"
MINUTES = 60

# Generator Image: Needs SWESmith dependencies for procedural generation
# We base this on a standard Ubuntu image since generation mostly involves
# cloning the repository and parsing its source code. 
generator_image = (
    modal.Image.from_registry("ubuntu:22.04", add_python="3.11")
    .apt_install("git")
    .pip_install_from_pyproject("pyproject.toml")
    .add_local_dir("swesmith", remote_path="/root/swesmith")
    .add_local_file(".env", remote_path="/root/.env")
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
    from swesmith.profiles import registry
    from swesmith.bug_gen.procedural.generate import main as generate_main
    from swesmith.bug_gen.collect_patches import main as collect_patches_main
    import traceback

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
        generate_main(
            repo=repo_id,
            max_bugs=max_bugs,
            seed=24,
            interleave=interleave
        )
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

    # Collect patches
    logs_dir = Path("logs/bug_gen")
    generated_repo_dirs = [d for d in logs_dir.iterdir() if d.is_dir()]
    if not generated_repo_dirs:
         return {"error": "No bug generation directory found after execution."}
    
    repo_id = generated_repo_dirs[0].name # Should only be one
    print(f"Detected repo_id: {repo_id}")
    
    # Run collection
    collect_patches_main(f"logs/bug_gen/{repo_id}")
    
    # Read artifacts
    artifacts = {}
    
    # Zip the bug gen dir
    shutil.make_archive(f"/tmp/{repo_id}", 'zip', f"logs/bug_gen/{repo_id}")
    with open(f"/tmp/{repo_id}.zip", "rb") as f:
        artifacts["bug_gen_zip"] = f.read()
        
    # Get the all_patches.json
    patches_file = logs_dir / f"{repo_id}_all_patches.json"
    if patches_file.exists():
        with open(patches_file, "r") as f:
            artifacts["patches_json"] = f.read()
            
    return artifacts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modal Bug Generation")
    parser.add_argument("--repo", required=True, help="Repository name (owner/repo)")
    parser.add_argument("--language", required=True, help="Language (e.g. javascript)")
    parser.add_argument("--max-bugs", type=int, default=200, help="Max bugs per modifier")
    parser.add_argument("--interleave", action="store_true", help="Interleave modifiers")
    
    args = parser.parse_args()

    
    print(f"Submitting bug generation task for {args.repo}...")
    with app.run():
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
        
    # Save artifacts
    if "patches_json" in results:
        patches = json.loads(results["patches_json"])
        if patches:
             # Extract repo_id from the first patch's instance_id
             first_id = patches[0]["instance_id"]
             repo_id = first_id.split(".func_pm")[0]
             
             # Create local dir
             local_bug_dir = Path(f"logs/bug_gen/{repo_id}")
             local_bug_dir.mkdir(parents=True, exist_ok=True)
             
             # Save patches json
             with open(f"logs/bug_gen/{repo_id}_all_patches.json", "w") as f:
                 f.write(results["patches_json"])
             print(f"Saved patches to logs/bug_gen/{repo_id}_all_patches.json")
             
             # Save zip content and unpack it
             if "bug_gen_zip" in results:
                 zip_path = local_bug_dir / "bugs.zip"
                 with open(zip_path, "wb") as f:
                     f.write(results["bug_gen_zip"])
                 subprocess.run(["unzip", "-o", str(zip_path), "-d", str(local_bug_dir)], check=True)
                 os.remove(zip_path)
                 print(f"Extracted bug details to {local_bug_dir}")
        else:
            print("No bugs were generated (patches list empty).")
    else:
        print("No patches_json returned.")
