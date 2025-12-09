
import argparse
import json
import logging
import os
from pathlib import Path

from swesmith.constants import LOG_DIR_ISSUE_GEN
from swebench.harness.constants import KEY_INSTANCE_ID

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def consolidate(dataset_path: str, output_path: str | None = None, model: str | None = None):
    """
    Consolidates generated issues into the dataset file.
    
    Args:
        dataset_path: Path to the JSON dataset file containing task instances.
        output_path: Optional path to write the consolidated dataset. If None, overwrites dataset_path.
        model: Optional model name to filter responses. If None, uses the first available model.
    """
    input_path = Path(dataset_path)
    if not input_path.exists():
        logger.error(f"Dataset path does not exist: {dataset_path}")
        return

    # Load original dataset
    try:
        data = json.loads(input_path.read_text())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse dataset file: {e}")
        return

    logger.info(f"Loaded {len(data)} instances from {dataset_path}")

    # Process each instance
    consolidated_count = 0
    missing_count = 0
    
    # We might generate multiple issues per instance (n > 1)
    # The current generate.py writes multiple responses to metadata["responses"][model]
    # We should expand these into multiple task instances if there are multiple responses
    
    new_data = []

    for instance in data:
        instance_id = instance.get(KEY_INSTANCE_ID)
        repo = instance.get("repo", "").split("/")[-1]
        
        # Look for the generated issue file
        # generate.py path: LOG_DIR_ISSUE_GEN / repo / f"{instance[KEY_INSTANCE_ID]}.json"
        
        # NOTE: If we want to support experiment_id in the future, we'd check subdirs.
        # But per current generate.py (without experiment_id), it's flat in repo dir.
        # We will assume flatness for now as requested "assuming all steps before... done"
        # and current generate.py doesn't use experiment_id.
        
        issue_file = LOG_DIR_ISSUE_GEN / repo / f"{instance_id}.json"
        
        if not issue_file.exists():
            # Try checking inside experiment subdirectories? 
            # The prompt implies we might have experiment_ids eventually 
            # but current generate.py puts them in logs/issue_gen/repo/
            # We will strictly look there.
            # However, if the user manually put them elsewhere, we might miss them.
            # We'll log a warning.
            logger.warning(f"Issue file not found for {instance_id}: {issue_file}")
            # Keep original instance? Or drop? Usually we want to keep valid ones.
            # If issue generation failed, maybe we shouldn't include it in final dataset for agents?
            # Steps 4+ usually require a problem_statement.
            # We will skip it if no problem statement is found? 
            # Or keep it without problem_statement (which might break downstream)?
            # Let's keep it but logging it.
            new_data.append(instance)
            missing_count += 1
            continue

        try:
            metadata = json.loads(issue_file.read_text())
        except Exception as e:
            logger.warning(f"Failed to read/parse {issue_file}: {e}")
            new_data.append(instance)
            missing_count += 1
            continue

        responses_map = metadata.get("responses", {})
        if not responses_map:
            logger.warning(f"No responses found in {issue_file}")
            new_data.append(instance)
            missing_count += 1
            continue

        # Determine which model to use
        target_model = model
        if not target_model:
            # Pick the first one available
            target_model = list(responses_map.keys())[0]
        
        if target_model not in responses_map:
             logger.warning(f"Model {target_model} not found in responses for {instance_id}. Available: {list(responses_map.keys())}")
             # Fallback to first available if designated model missing?
             # Let's strictly require it if specified, else fail for this inst.
             if model: # if user specified a model explicitly
                 new_data.append(instance)
                 missing_count += 1
                 continue
             else:
                 target_model = list(responses_map.keys())[0]

        problem_statements = responses_map[target_model]
        
        if not problem_statements:
            logger.warning(f"Empty problem statements list for {instance_id}")
            new_data.append(instance)
            missing_count += 1
            continue

        # Expand instances, picking first statement
        for stmt in problem_statements[:1]:
            new_inst = instance.copy()
            new_inst["problem_statement"] = stmt
            
            new_data.append(new_inst)
            consolidated_count += 1

    # Write output
    final_output_path = output_path if output_path else dataset_path
    logger.info(f"Consolidated {consolidated_count} issues (missed {missing_count})")
    logger.info(f"Writing to {final_output_path}")
    
    with open(final_output_path, "w") as f:
        json.dump(new_data, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consolidate generated issues into task instances dataset.")
    parser.add_argument("dataset_path", help="Path to the JSON dataset file containing task instances")
    parser.add_argument("--output_path", help="Output path for consolidated dataset. Defaults to overwriting input.", default=None)
    parser.add_argument("--model", help="Specific model name to retrieve responses for", default=None)
    
    args = parser.parse_args()
    
    consolidate(args.dataset_path, args.output_path, args.model)
