import os

LOG_DIR = "logs/bug_gen"

def count_combined_bugs():
    combine_file_count = 0
    combine_module_count = 0
    
    if not os.path.exists(LOG_DIR):
        print(f"Directory {LOG_DIR} does not exist.")
        return

    for root, dirs, files in os.walk(LOG_DIR):
        for file in files:
            if file.startswith("metadata__combine_file__") and file.endswith(".json"):
                combine_file_count += 1
            elif file.startswith("metadata__combine_module__") and file.endswith(".json"):
                combine_module_count += 1
                
    print(f"Total combine_file bugs: {combine_file_count}")
    print(f"Total combine_module bugs: {combine_module_count}")
    print(f"Total combined bugs: {combine_file_count + combine_module_count}")

if __name__ == "__main__":
    count_combined_bugs()
