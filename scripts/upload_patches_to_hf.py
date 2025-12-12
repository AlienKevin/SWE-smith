import glob
import json
import os
from datasets import Dataset, DatasetDict

def extract_modifier(instance_id):
    """
    Extracts the modifier from the instance_id.
    e.g. "google__gson.dd2fe59c.func_pm_string_literal_change__fci23mvv" => "func_pm_string_literal_change"
         "instance_id": "google__gson.dd2fe59c.combine_module__1z8dk02p" => "combine_module"
    """
    parts = instance_id.split('.')
    if len(parts) < 3:
        return "unknown"
    
    # The modifier is usually the 3rd part, but we need to strip the unique suffix (last part after __)
    # Actually looking at examples: 
    # google__gson.dd2fe59c.func_pm_string_literal_change__fci23mvv
    # The 3rd part is "func_pm_string_literal_change__fci23mvv" if split by dot? 
    # PROBABLY NOT. "google__gson" is part 1? NO. 
    # Let's assume standard split by dot:
    # 0: google__gson
    # 1: dd2fe59c
    # 2: func_pm_string_literal_change__fci23mvv
    
    # We want "func_pm_string_literal_change" from "func_pm_string_literal_change__fci23mvv"
    
    modifier_part = parts[2]
    if "__" in modifier_part:
        return modifier_part.split("__")[0]
    return modifier_part

def process_file(file_path):
    try:
        with open(file_path, 'r') as f:
            if os.stat(file_path).st_size == 0:
                print(f"Warning: {file_path} is empty. Skipping.")
                return []
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON in {file_path}: {e}. Skipping.")
        return []
    
    processed_items = []
    for item in data:
        instance_id = item.get("instance_id", "")
        modifier = extract_modifier(instance_id)
        
        patch_content = item.get("patch", "")
        repo = item.get("repo", "")
        
        # Default single patch values
        num_patches = 1
        patch_ids = [instance_id]
        
        if "patch_files" in item: # combine_file type
            # map "patch_files" to "patch_ids" and "num_patch_files" to "num_patches"
            patch_ids = item["patch_files"]
            num_patches = item.get("num_patch_files", len(patch_ids))
        elif "patch_ids" in item: # combine_module type
            patch_ids = item["patch_ids"]
            num_patches = item.get("num_patches", len(patch_ids))
        else:
            # It's a single patch, using defaults
            pass
            
        processed_items.append({
            "instance_id": instance_id,
            "patch": patch_content,
            "repo": repo,
            "num_patches": num_patches,
            "patch_ids": patch_ids,
            "modifier": modifier
        })
    return processed_items

def main():
    base_dir = "all_patches"
    languages = ['cpp', 'java', 'js', 'rust']
    
    dataset_dict = {}
    
    for lang in languages:
        print(f"Processing language: {lang}")
        lang_dir = os.path.join(base_dir, lang)
        
        # recursive glob to find all _all_patches.json
        # pattern might be just inside the lang dir or nested?
        # User said "under all_patches", structure showed:
        # cpp/
        #   catchorg__Catch2.9b3f508a_all_patches.json
        # So it seems flat under lang dir.
        
        pattern = os.path.join(lang_dir, "*_all_patches.json")
        files = glob.glob(pattern)
        
        all_lang_items = []
        for file_path in files:
            print(f"  Reading {file_path}...")
            items = process_file(file_path)
            all_lang_items.extend(items)
            
        if not all_lang_items:
            print(f"Warning: No items found for {lang}")
            continue
            
        print(f"  Found {len(all_lang_items)} items for {lang}")
        
        # Create Dataset
        dataset = Dataset.from_list(all_lang_items)
        dataset_dict[lang] = dataset
        
    final_dataset = DatasetDict(dataset_dict)
    
    print("\nPushing to Hub...")
    final_dataset.push_to_hub("AlienKevin/Multi-SWE-smith-tasks")
    print("Done!")

if __name__ == "__main__":
    main()
