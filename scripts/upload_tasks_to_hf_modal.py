import modal
import json
import asyncio
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor

# Define Modal App
app = modal.App("swesmith-upload-hf")
vol = modal.Volume.from_name("swesmith-bug-gen")

# Define an image with necessary dependencies
# We need datasets and huggingface_hub for the remote push
image = modal.Image.debian_slim().pip_install("tqdm", "datasets", "huggingface_hub")


def _process_single_task(task, issue_gen_dir, repo_id):
    """Helper to process a single task instance"""
    instance_id = task.get("instance_id")
    if not instance_id:
        return task

    if "image_name" in task and ".architecture." in task["image_name"]:
        task["image_name"] = task["image_name"].replace(".architecture", "")

    task["problem_statement"] = ""
    issue_file = issue_gen_dir / repo_id / f"{instance_id}.json"

    if issue_file.exists():
        try:
            with open(issue_file, "r") as f_issue:
                issue_data = json.load(f_issue)
                resp = issue_data.get("responses", {})
                if "portkey/gpt-5-mini" in resp:
                    content = resp["portkey/gpt-5-mini"]
                    if isinstance(content, list) and len(content) > 0:
                        task["problem_statement"] = content[0]
        except Exception:
            pass
    return task


@app.function(image=image, volumes={"/data": vol}, timeout=1200, max_containers=10)
def process_repo(task_filename: str):
    """(Same as before)"""
    import concurrent.futures

    # Assume language is javascript for now or pass it in path
    language = "javascript"
    task_file_path = Path(f"/data/{language}/task_insts/{task_filename}")
    issue_gen_dir = Path(f"/data/{language}/issue_gen")

    tasks_out = []

    if not task_file_path.exists():
        print(f"File not found: {task_file_path}")
        return []

    repo_id = task_file_path.stem
    try:
        with open(task_file_path, "r") as f:
            tasks = json.load(f)

        print(f"[{repo_id}] Processing {len(tasks)} tasks...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(_process_single_task, task, issue_gen_dir, repo_id)
                for task in tasks
            ]

            for future in concurrent.futures.as_completed(futures):
                tasks_out.append(future.result())

    except Exception as e:
        print(f"[{repo_id}] Error: {e}")

    return tasks_out


@app.function(
    image=image, secrets=[modal.Secret.from_name("john-hf-secret")], timeout=1800
)
def push_to_hf_remote(all_tasks: list, target_dataset: str):
    import os
    from datasets import load_dataset, Dataset, concatenate_datasets
    from huggingface_hub import create_repo, HfApi

    print(f"Starting remote upload to {target_dataset}")
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("WARNING: HF_TOKEN not found in environment variables!")
    else:
        print("HF_TOKEN found in environment variables.")

    # Validation
    required_keys = [
        "instance_id",
        "patch",
        "FAIL_TO_PASS",
        "PASS_TO_PASS",
        "image_name",
        "repo",
    ]
    print("Validating keys...")
    cleaned_tasks = []
    for task in all_tasks:
        valid = True
        for k in required_keys:
            if k not in task:
                print(f"Missing key {k} in task {task.get('instance_id')}. Skipping.")
                valid = False
                break
        if not valid:
            continue

        if "problem_statement" not in task:
            task["problem_statement"] = ""
        cleaned_tasks.append(task)

    print(f"Valid tasks: {len(cleaned_tasks)}")
    local_dataset = Dataset.from_list(cleaned_tasks)
    local_ids = set(local_dataset["instance_id"])

    final_dataset = local_dataset

    # Try to ensure repo exists
    print(f"Ensuring repository {target_dataset} exists...")
    try:
        create_repo(target_dataset, repo_type="dataset", token=token, exist_ok=True)
    except Exception as e:
        print(
            f"Warning: create_repo failed: {e}. Attempting upload anyway (might fail if permissions wrong)."
        )

    # print(f"Loading target dataset: {target_dataset}")
    # try:
    #     sweb = load_dataset(target_dataset, split="train", token=token)
    #     print(f"Existing HF dataset size: {len(sweb)}")

    #     sweb_filtered = sweb.filter(lambda x: x["instance_id"] not in local_ids)
    #     print(f"Would override {len(sweb) - len(sweb_filtered)} instances")

    #     final_dataset = concatenate_datasets([sweb_filtered, local_dataset])
    # except Exception as e:
    #     print(f"Note: Could not load existing dataset '{target_dataset}' (it might be new or empty). Error: {e}")
    #     print("Proceeding with creating a new dataset from local tasks.")

    print(f"Pushing {len(final_dataset)} instances to {target_dataset}...")
    final_dataset.push_to_hub(target_dataset, token=token)
    print("Remote push finished successfully.")


@app.local_entrypoint()
def main(target_dataset: str = "SWE-bench/SWE-smith-js", push: bool = False):
    print("Listing task files from Modal volume...")
    try:
        entries = vol.listdir("javascript/task_insts")
        filenames = [e.path.split("/")[-1] for e in entries if e.path.endswith(".json")]
    except Exception as e:
        print(f"Error listing volume: {e}")
        return

    print(f"Found {len(filenames)} files. Starting parallel processing...")

    all_tasks = []
    for repo_tasks in process_repo.map(filenames):
        all_tasks.extend(repo_tasks)

    print(f"Fetched total {len(all_tasks)} task instances.")

    if not push:
        confirm = input(f"Ready to push to HF. Proceed? (y/n) ").lower()
        if confirm != "y":
            print("Aborting.")
            return

    print("Launching remote push job...")
    push_to_hf_remote.remote(all_tasks, target_dataset)
    print("Done!")
