#!/usr/bin/env python3
"""
Script to find specific diff files in bug generation logs.
"""

import os
import sys
from pathlib import Path


def find_diff_file(base_dir: str, filename: str) -> list[Path]:
    """
    Search for a specific diff file within a directory tree.
    
    Args:
        base_dir: Root directory to search from
        filename: Name of the diff file to find
        
    Returns:
        List of Path objects for all matching files
    """
    base_path = Path(base_dir)
    if not base_path.exists():
        print(f"Error: Directory '{base_dir}' does not exist")
        return []
    
    matches = []
    for path in base_path.rglob(filename):
        if path.is_file():
            matches.append(path)
    
    return matches


def main():
    # Configuration
    base_dir = "/home/ubuntu/SWE-smith/logs/bug_gen/BurntSushi__rust-csv.da000888/"
    target_file = "bug__func_pm_ctrl_shuffle__piouamyx.diff"
    
    # Allow command-line override
    if len(sys.argv) > 1:
        base_dir = sys.argv[1]
    if len(sys.argv) > 2:
        target_file = sys.argv[2]
    
    print(f"Searching for '{target_file}' in '{base_dir}'...")
    print("-" * 80)
    
    matches = find_diff_file(base_dir, target_file)
    
    if matches:
        print(f"Found {len(matches)} match(es):\n")
        for i, match in enumerate(matches, 1):
            print(f"{i}. {match}")
            print(f"   Size: {match.stat().st_size} bytes")
            print()
    else:
        print(f"No matches found for '{target_file}'")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


"""
Expected to find two identical rewrites in two different files:

diff --git a/examples/tutorial-read-serde-03.rs b/examples/tutorial-read-serde-03.rs
index 022e246..7859220 100644
--- a/examples/tutorial-read-serde-03.rs
+++ b/examples/tutorial-read-serde-03.rs
@@ -6,11 +6,11 @@ use std::{error::Error, io, process};
 type Record = HashMap<String, String>;
 
 fn run() -> Result<(), Box<dyn Error>> {
-    let mut rdr = csv::Reader::from_reader(io::stdin());
     for result in rdr.deserialize() {
         let record: Record = result?;
         println!("{:?}", record);
     }
+    let mut rdr = csv::Reader::from_reader(io::stdin());
     Ok(())
 }


diff --git a/examples/tutorial-read-serde-invalid-01.rs b/examples/tutorial-read-serde-invalid-01.rs
index 3ea836d..058846b 100644
--- a/examples/tutorial-read-serde-invalid-01.rs
+++ b/examples/tutorial-read-serde-invalid-01.rs
@@ -14,11 +14,11 @@ struct Record {
 }
 
 fn run() -> Result<(), Box<dyn Error>> {
-    let mut rdr = csv::Reader::from_reader(io::stdin());
     for result in rdr.deserialize() {
         let record: Record = result?;
         println!("{:?}", record);
     }
+    let mut rdr = csv::Reader::from_reader(io::stdin());
     Ok(())
 }

"""