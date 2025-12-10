import glob
import json
import os


def main():
    # Input directory containing the trajectory files
    input_dir = "trajectories_glm_sft"
    # Output file path
    output_file = "trajectories_glm_sft.jsonl"
    
    # Check if input directory exists
    if not os.path.exists(input_dir):
        print(f"Error: Directory '{input_dir}' not found.")
        return

    # Pattern to match jsonl files
    files = glob.glob(os.path.join(input_dir, "*.jsonl"))
    print(f"Found {len(files)} files in {input_dir}")

    count = 0
    total_count = 0
    with open(output_file, 'w') as outfile:
        for filename in files:
            with open(filename, 'r') as infile:
                for line in infile:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        total_count += 1
                        # Filter out those with resolved = False (keep resolved = True)
                        # The key in the JSON is observed to be "resolved"
                        if data.get("resolved") is True:
                            outfile.write(line)
                            count += 1
                    except json.JSONDecodeError:
                        print(f"Error decoding JSON in file: {filename}")
                        continue
    
    print(f"Resolved trajectories: {count}")
    print(f"Total trajectories generated: {total_count}")
    print(f"Collected {count} resolved trajectories into {output_file}")

if __name__ == "__main__":
    main()
