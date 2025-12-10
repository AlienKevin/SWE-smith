import os
import json
import glob

target_dir = "SWE-agent/trajectories/ubuntu/swesmith_infer__openai--SWE-agent-LM-32B-Rust-glm-142-epoch-2__t-0.00__p-1.00__c-0.00___swe_bench_multilingual_rust"
output_file = os.path.join(target_dir, "preds.json")

preds = {}
pred_files = glob.glob(os.path.join(target_dir, "**/*.pred"), recursive=True)

print(f"Found {len(pred_files)} .pred files.")

for pred_file in pred_files:
    try:
        with open(pred_file, "r") as f:
            content = f.read().strip()
            if not content:
                print(f"Warning: {pred_file} is empty.")
                continue
            
            # Try to parse as JSON
            data = json.loads(content)
            
            # Check if it has the required fields
            if "instance_id" in data:
                preds[data["instance_id"]] = data
            else:
                print(f"Skipping {pred_file}: Missing 'instance_id'")
                
    except json.JSONDecodeError:
        print(f"Warning: {pred_file} is not valid JSON. First 50 chars: {content[:50]}")
        # Try to infer instance_id from filename?
        # Filename format: .../<instance_id>/<instance_id>.pred
        basename = os.path.basename(pred_file)
        instance_id = basename.replace(".pred", "")
        
        # Construct a prediction object assuming the content IS the patch (or maybe meaningless text?)
        # But earlier we saw `burntsushi__ripgrep-2209.pred` containing text that didn't look like a patch (no diff header).
        # We will add it anyway but maybe flag it? 
        # Actually, let's see how many fail first.
        pass

print(f"Aggregated {len(preds)} predictions.")

with open(output_file, "w") as f:
    json.dump(preds, f, indent=4)
    
print(f"Saved to {output_file}")
