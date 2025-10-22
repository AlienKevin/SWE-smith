#!/usr/bin/env python3
"""
Test Rust procedural bug generation locally without requiring mirror repos.

This script clones repos directly from their original sources and runs
procedural bug generation locally.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from swesmith.profiles import registry
from swesmith.bug_gen.procedural import MAP_EXT_TO_MODIFIERS
from swesmith.bug_gen.adapters import get_entities_from_file


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


def clone_repo_directly(owner, repo, commit, dest):
    """Clone repository directly from GitHub without using mirrors."""
    if os.path.exists(dest):
        print(f"  Repository already exists at {dest}, skipping clone")
        return True
    
    print(f"  Cloning {owner}/{repo} at {commit}...")
    try:
        subprocess.run(
            f"git clone https://github.com/{owner}/{repo}.git {dest}",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        subprocess.run(
            f"cd {dest} && git checkout {commit}",
            shell=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        if os.path.exists(os.path.join(dest, ".gitmodules")):
            subprocess.run(
                f"cd {dest} && git submodule update --init --recursive",
                shell=True,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        
        print(f"  ✓ Cloned successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to clone: {e}")
        return False


def generate_bugs_for_profile(repo_id, max_bugs=50):
    """Generate bugs for a single profile."""
    print(f"\n{'='*80}")
    print(f"Processing: {repo_id}")
    print(f"{'='*80}")
    
    try:
        rp = registry.get(repo_id)
    except Exception as e:
        print(f"✗ Failed to get profile: {e}")
        return False
    
    repo_dir = f"repos_local/{repo_id}"
    os.makedirs("repos_local", exist_ok=True)
    
    if not clone_repo_directly(rp.owner, rp.repo, rp.commit, repo_dir):
        return False
    
    print(f"  Extracting code entities...")
    entities = []
    for root, _, files in os.walk(repo_dir):
        for file in files:
            if "test" in file.lower() or "test" in root.lower():
                continue
            
            file_path = os.path.join(root, file)
            file_ext = Path(file_path).suffix
            
            if file_ext == ".rs":
                try:
                    get_entities_from_file[file_ext](entities, file_path, max_bugs)
                except Exception as e:
                    print(f"  Warning: Failed to parse {file_path}: {e}")
                    continue
    
    print(f"  Found {len(entities)} code entities")
    
    if len(entities) == 0:
        print(f"  ✗ No entities found")
        return False
    
    rust_modifiers = MAP_EXT_TO_MODIFIERS.get(".rs", [])
    print(f"  Using {len(rust_modifiers)} Rust modifiers")
    
    bug_count = 0
    output_dir = Path(f"logs/bug_gen/{repo_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for entity in entities:
        if bug_count >= max_bugs * len(rust_modifiers):
            break
        
        for modifier in rust_modifiers:
            if bug_count >= max_bugs * len(rust_modifiers):
                break
            
            try:
                if not modifier.can_change(entity):
                    continue
                
                bug_rewrite = modifier.modify(entity)
                if bug_rewrite is None:
                    continue
                
                entity_name = entity.name.replace("/", "_").replace(" ", "_")
                file_rel_path = os.path.relpath(entity.file_path, repo_dir).replace("/", "__")
                bug_dir = output_dir / file_rel_path / entity_name
                bug_dir.mkdir(parents=True, exist_ok=True)
                
                bug_hash = bug_rewrite.get_hash()
                bug_file = bug_dir / f"bug__{modifier.name}__{bug_hash}.diff"
                metadata_file = bug_dir / f"metadata__{modifier.name}__{bug_hash}.json"
                
                original_code = entity.src_code
                modified_code = bug_rewrite.rewrite
                
                diff_content = f"""--- a/{os.path.relpath(entity.file_path, repo_dir)}
+++ b/{os.path.relpath(entity.file_path, repo_dir)}
@@ -1,1 +1,1 @@
-{original_code}
+{modified_code}
"""
                
                with open(bug_file, "w") as f:
                    f.write(diff_content)
                
                metadata = {
                    "file_path": entity.file_path,
                    "entity_name": entity.name,
                    "modifier": modifier.name,
                    "explanation": bug_rewrite.explanation,
                    "strategy": bug_rewrite.strategy,
                    "cost": bug_rewrite.cost,
                }
                
                with open(metadata_file, "w") as f:
                    json.dump(metadata, f, indent=2)
                
                bug_count += 1
                
            except Exception as e:
                print(f"  Warning: Failed to generate bug with {modifier.name}: {e}")
                continue
    
    print(f"  ✓ Generated {bug_count} bugs")
    
    print(f"  Collecting patches...")
    patches_file = f"logs/bug_gen/{repo_id}_all_patches.json"
    
    all_patches = []
    for bug_file in output_dir.rglob("bug__*.diff"):
        metadata_file = bug_file.parent / bug_file.name.replace("bug__", "metadata__").replace(".diff", ".json")
        
        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
            
            with open(bug_file, "r") as f:
                patch = f.read()
            
            instance_id = f"{repo_id}.{bug_file.stem.replace('bug__', '')}"
            
            all_patches.append({
                "instance_id": instance_id,
                "patch": patch,
                "metadata": metadata,
            })
    
    with open(patches_file, "w") as f:
        json.dump(all_patches, f, indent=2)
    
    print(f"  ✓ Collected {len(all_patches)} patches to {patches_file}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Test Rust procedural bug generation locally"
    )
    parser.add_argument(
        "--max-bugs",
        type=int,
        default=50,
        help="Maximum bugs per modifier per repo (default: 50)",
    )
    parser.add_argument(
        "--profiles",
        nargs="+",
        default=None,
        help="Specific profiles to test (default: all Rust profiles)",
    )
    
    args = parser.parse_args()
    
    profiles_to_test = args.profiles if args.profiles else RUST_PROFILES
    
    print(f"Testing {len(profiles_to_test)} Rust profiles")
    print(f"Max bugs per modifier: {args.max_bugs}")
    
    successful = 0
    failed = 0
    failed_profiles = []
    
    for repo_id in profiles_to_test:
        if generate_bugs_for_profile(repo_id, args.max_bugs):
            successful += 1
        else:
            failed += 1
            failed_profiles.append(repo_id)
    
    print(f"\n{'='*80}")
    print(f"Testing Complete!")
    print(f"{'='*80}")
    print(f"Successful: {successful}/{len(profiles_to_test)}")
    print(f"Failed: {failed}/{len(profiles_to_test)}")
    
    if failed_profiles:
        print(f"\nFailed profiles:")
        for profile in failed_profiles:
            print(f"  - {profile}")
    
    print(f"\nNext steps:")
    print(f"  1. Run validation: python -m swesmith.harness.valid logs/bug_gen/<repo_id>_all_patches.json")
    print(f"  2. Analyze results: python scripts/analyze_bugs.py <repo_id>")
    print(f"  3. Generate comprehensive report: python scripts/analyze_rust_comprehensive.py")


if __name__ == "__main__":
    main()
