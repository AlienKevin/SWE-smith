import glob
import json
import matplotlib.pyplot as plt
import numpy as np
import tiktoken

def main():
    files = glob.glob("trajectories_glm_sft/*.jsonl")
    if not files:
        print("No matching files found.")
        return

    turn_counts = []
    token_counts = []
    enc = tiktoken.encoding_for_model("gpt-5-mini")
    
    for filename in files:
        # print(f"Processing {filename}...")
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Assuming 'messages' is a list of message objects
                    messages = data.get('messages', [])
                    turn_counts.append(len(messages) // 2)
                    
                    # Count tokens
                    total_tokens = 0
                    for message in messages:
                        content = message.get('content', '')
                        if content:
                            total_tokens += len(enc.encode(content))
                    token_counts.append(total_tokens)
                except json.JSONDecodeError:
                    print(f"Error decoding JSON in {filename}")

    if not turn_counts:
        print("No trajectories found.")
        return

    min_turns = np.min(turn_counts)
    avg_turns = np.mean(turn_counts)
    max_turns = np.max(turn_counts)

    print(f"Min turns: {min_turns}")
    print(f"Average turns: {avg_turns:.2f}")
    print(f"Max turns: {max_turns}")

    # Plot histogram
    plt.figure(figsize=(10, 6))
    # Use bins centered on integers
    bins = np.arange(min_turns, max_turns + 2) - 0.5
    plt.hist(turn_counts, bins=bins, edgecolor='black')
    
    plt.title('Histogram of Conversation Turns (Messages)')
    plt.xlabel('Number of Turns')
    plt.ylabel('Frequency')
    plt.grid(axis='y', alpha=0.75)
    
    output_image = "turns.png"
    plt.savefig(output_image)
    print(f"Histogram saved to {output_image}")

    # Process token counts
    min_tokens = np.min(token_counts)
    avg_tokens = np.mean(token_counts)
    max_tokens = np.max(token_counts)

    print(f"\nMin tokens: {min_tokens}")
    print(f"Average tokens: {avg_tokens:.2f}")
    print(f"Max tokens: {max_tokens}")

    # Plot histogram for tokens
    plt.figure(figsize=(10, 6))
    # Use bins automatically or defined
    plt.hist(token_counts, bins=30, edgecolor='black')
    
    plt.title('Histogram of Trajectory Lengths (Tokens)')
    plt.xlabel('Number of Tokens')
    plt.ylabel('Frequency')
    plt.grid(axis='y', alpha=0.75)
    
    output_image_tokens = "trajectory_lengths.png"
    plt.savefig(output_image_tokens)
    print(f"Token histogram saved to {output_image_tokens}")

if __name__ == "__main__":
    main()
