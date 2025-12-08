import json
import glob
from transformers import AutoTokenizer
import os

def count_tokens():
    model_id = "Qwen/Qwen2.5-Coder-32B-Instruct"
    print(f"Loading tokenizer for {model_id}...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id)
    except Exception as e:
        print(f"Error loading tokenizer: {e}")
        return

    total_tokens = 0
    file_pattern = "swesmith_gen__glm__*.xml.jsonl"
    files = glob.glob(file_pattern)
    
    print(f"Found {len(files)} files matching {file_pattern}")

    trajectory_lengths = []

    for file_path in files:
        print(f"Processing {file_path}...")
        file_tokens = 0
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if 'messages' in data:
                            messages = data['messages']
                            # Encode messages using chat template
                            tokens = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=False)
                            num_tokens = len(tokens)
                            file_tokens += num_tokens
                            trajectory_lengths.append(num_tokens)
                    except json.JSONDecodeError:
                        print(f"Skipping invalid JSON line in {file_path}")
                    except Exception as e:
                        print(f"Error processing line in {file_path}: {e}")
            
            print(f"  Tokens in {file_path}: {file_tokens}")
            total_tokens += file_tokens
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")

    print(f"\nTotal tokens across all files: {total_tokens}")

    if trajectory_lengths:
        import statistics
        mean_length = statistics.mean(trajectory_lengths)
        std_length = statistics.stdev(trajectory_lengths) if len(trajectory_lengths) > 1 else 0.0
        print(f"Mean trajectory length: {mean_length:.2f}")
        print(f"Standard deviation of trajectory length: {std_length:.2f}")
    else:
        print("No trajectories found.")

    # Generate histogram
    try:
        import matplotlib.pyplot as plt
        
        plt.figure(figsize=(10, 6))
        plt.hist(trajectory_lengths, bins=20, edgecolor='black')
        plt.title('Distribution of Trajectory Lengths', fontsize=16)
        plt.xlabel('Trajectory Length (Tokens)', fontsize=14)
        plt.ylabel('Frequency', fontsize=14)
        plt.xticks(fontsize=12)
        plt.yticks(fontsize=12)
        plt.tight_layout()
        plt.savefig('trajectory_lengths.png')
        print("Histogram saved as trajectory_lengths.png")
    except ImportError:
        print("matplotlib not found. Skipping histogram generation.")
    except Exception as e:
        print(f"Error generating histogram: {e}")

if __name__ == "__main__":
    count_tokens()
