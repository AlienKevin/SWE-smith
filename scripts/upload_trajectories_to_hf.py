import os
import glob
import json
from datasets import Dataset, DatasetDict
from huggingface_hub import HfApi, HfFileSystem

# Configuration
REPO_ID = "AlienKevin/SWE-bench-Multilingual-trajectories"
BASE_DIR = "/home/ubuntu/SWE-smith/SWE-agent/trajectories/ubuntu"
EVAL_TRAJECTORIES_DIR = "/home/ubuntu/SWE-smith/SWE-bench"

# Split configuration
SPLIT_CONFIG = {
    "Qwen2.5-Coder-32B-Instruct": {
        "traj_dir": "swesmith_infer__openai--Qwen--Qwen2.5-Coder-32B-Instruct__t-0.00__p-1.00__c-0.00___swe_bench_multilingual_rust",
        "eval_json": "swesmith_infer__openai--Qwen--Qwen2.5-Coder-32B-Instruct__t-0.00__p-1.00__c-0.00___swe_bench_multilingual_rust.multilingual_rust_eval_qwen2.5-coder-32b-instruct.json"
    },
    "Multi-SWE-agent-32B-Rust": {
        "traj_dir": "swesmith_infer__openai--SWE-agent-LM-32B-Rust-glm-142-epoch-2__t-0.00__p-1.00__c-0.00___swe_bench_multilingual_rust",
        "eval_json": "swesmith_infer__openai--SWE-agent-LM-32B-Rust-glm-142-epoch-2__t-0.00__p-1.00__c-0.00___swe_bench_multilingual_rust.multilingual_rust_eval_swe_agent_lm_32b_rust_glm_142_epoch_2.json"
    },
    "SWE-agent-LM-32B": {
        "traj_dir": "swesmith_infer__openai--SWE-bench--SWE-agent-LM-32B__t-0.00__p-1.00__c-0.00___swe_bench_multilingual_rust",
        "eval_json": "swesmith_infer__openai--SWE-bench--SWE-agent-LM-32B__t-0.00__p-1.00__c-0.00___swe_bench_multilingual_rust.multilingual_rust_eval.json"
    }
}

def load_eval_data(eval_json_path):
    """Loads resolved, errored, and completed IDs from the evaluation JSON."""
    if not os.path.exists(eval_json_path):
        print(f"Warning: Eval JSON not found at {eval_json_path}")
        return set(), set(), set()
    
    with open(eval_json_path, 'r') as f:
        data = json.load(f)
        
    resolved_ids = set(data.get("resolved_ids", []))
    error_ids = set(data.get("error_ids", []))
    completed_ids = set(data.get("completed_ids", []))
    
    return resolved_ids, error_ids, completed_ids

def process_split(split_name, config):
    print(f"Processing split: {split_name}")
    traj_base_path = os.path.join(BASE_DIR, config["traj_dir"])
    eval_json_path = os.path.join(EVAL_TRAJECTORIES_DIR, config["eval_json"])
    
    resolved_ids, error_ids, completed_ids = load_eval_data(eval_json_path)
    
    data_list = []
    
    # Walk through the directory to find subfolders with .traj files
    if not os.path.exists(traj_base_path):
        print(f"Error: Trajectory directory not found: {traj_base_path}")
        return []

    # Get all subdirectories
    subdirs = [d for d in os.listdir(traj_base_path) if os.path.isdir(os.path.join(traj_base_path, d))]
    
    for subdir in subdirs:
        subdir_path = os.path.join(traj_base_path, subdir)
        traj_files = glob.glob(os.path.join(subdir_path, "*.traj"))
        
        if traj_files:
            # Assuming one traj file per folder, or pick the first one
            traj_file = traj_files[0] 
            
            with open(traj_file, 'r') as f:
                content = f.read()
                
            task_id = subdir # The subfolder name is the ID
            
            entry = {
                "id": task_id,
                "trajectory": content,
                "resolved": task_id in resolved_ids,
                "errored": task_id in error_ids,
                "completed": task_id in completed_ids
            }
            data_list.append(entry)
            
    print(f"  Found {len(data_list)} trajectories for {split_name}")
    return data_list

def main():
    splits = {}
    
    for split_name, config in SPLIT_CONFIG.items():
        data = process_split(split_name, config)
        if data:
            splits[split_name] = Dataset.from_list(data)
        else:
             # handle empty split if necessary, or just warn
             print(f"Warning: No data found for split {split_name}")

    dataset_dict = DatasetDict({k.replace("-", "_"): v for k, v in splits.items()})
    
    if len(dataset_dict) > 0:
        print("Pushing dataset to Hub...")
        dataset_dict.push_to_hub(REPO_ID)
        
        # Create README
        readme_content = """---
license: mit
---

# SWE-bench Multilingual Trajectories

This dataset contains trajectories from different models evaluated on SWE-bench Multilingual (Rust).

## Splits

- **Qwen2_5_Coder_32B_Instruct**: Trajectories from Qwen2.5-Coder-32B-Instruct.
- **SWE_agent_LM_32B**: Trajectories from SWE-agent-LM-32B (from SWE-smith).
- **Multi_SWE_agent_32B_Rust**: Trajectories from Multi-SWE-agent-32B-Rust, trained on 142 trajectories sampled from GLM 4.6 on a subset of Rust task instances from Multi-SWE-smith for 3 epochs.

## Columns

- `id`: The task instance ID (subfolder name).
- `trajectory`: The content of the `*.traj` file in JSON format.
- `resolved`: Boolean indicating if the task was resolved.
- `errored`: Boolean indicating if the task execution errored.
- `completed`: Boolean indicating if the task was completed (submitted).
"""
        # Upload README
        api = HfApi()
        api.upload_file(
            path_or_fileobj=readme_content.encode('utf-8'),
            path_in_repo="README.md",
            repo_id=REPO_ID,
            repo_type="dataset"
        )
        print("README uploaded.")
    else:
        print("No data collected for any split. Nothing to upload.")

if __name__ == "__main__":
    main()
