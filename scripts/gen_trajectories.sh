#!/bin/bash


# Define excluded repositories (Owner__Repo format)
EXCLUDED_REPOS=(
    "tokio-rs__tokio"
    "uutils__coreutils"
    "nushell__nushell"
    "tokio-rs__axum"
    "BurntSushi__ripgrep"
    "sharkdp__bat"
    "astral-sh__ruff"
)

# Determine optimal number of workers
NUM_WORKERS=$(nproc)
echo "Using $NUM_WORKERS workers for parallel processing"

# Function to check if a repo is excluded
is_excluded() {
    local repo_name=$1
    for excluded in "${EXCLUDED_REPOS[@]}"; do
        if [[ "$repo_name" == "$excluded"* ]]; then
            return 0
        fi
    done
    return 1
}

# Iterate over all directories in logs/bug_gen
for repo_dir in logs/bug_gen/*; do
    if [ ! -d "$repo_dir" ]; then
        continue
    fi

    repo=$(basename "$repo_dir")
    
    # Check for exclusion
    if is_excluded "$repo"; then
        echo "Skipping excluded repository: $repo"
        continue
    fi

    echo "===================================="
    echo "Generating Trajectories for $repo"
    echo "===================================="

    # Cleanup: Remove local branches from previous runs
    if [ -d "$repo" ]; then
        echo ""
        echo "Cleaning up local repository branches..."
        cd "$repo"
        # Get current branch
        current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")
        # Switch to main if not already there
        if [ "$current_branch" != "main" ]; then
            git checkout main 2>/dev/null || git checkout master 2>/dev/null || true
        fi
        # Delete all local branches except main/master
        git branch | grep -v -E "^\*|main|master" | xargs -r git branch -D 2>/dev/null || true
        git reset --hard 2>/dev/null || true
        cd ..
        echo "✓ Cleaned up local branches"
    fi

    # Step 0: Ensure mirror repository exists
    echo ""
    echo "[Step 0/6] Creating mirror repository..."
    if ! python -c "from swesmith.profiles import registry; registry.get('$repo').create_mirror()"; then
        echo "❌ Step 0 failed: Could not create mirror for $repo"
        continue
    fi
    echo "✓ Mirror repository ready"

    # Step 1: Collect task instances with 1+ Fail-to-Pass tests
    echo ""
    echo "[Step 1/6] Gathering validated task instances..."
    if ! python -m swesmith.harness.gather logs/run_validation/$repo --override_branch --debug_subprocess; then
        echo "❌ Step 1 failed: Could not gather task instances for $repo"
        continue
    fi

    # Step 2: Run evaluation to generate gold trajectories
    echo ""
    echo "[Step 2/6] Running evaluation (generating gold trajectories)..."
    if ! python -m swesmith.harness.eval \
        --dataset_path logs/task_insts/$repo.json \
        --predictions_path gold \
        --run_id $repo \
        --workers $NUM_WORKERS; then
        echo "❌ Step 2 failed: Gold evaluation failed for $repo"
        continue
    fi

    # Step 3: Generate issues for the task instances
    echo ""
    echo "[Step 3/6] Generating issue descriptions..."
    if ! python -m swesmith.issue_gen.generate \
        --dataset_path logs/task_insts/$repo.json \
        --config_file configs/issue_gen/ig_v2.yaml \
        --workers $NUM_WORKERS \
        --redo_existing; then
        echo "❌ Step 3 failed: Issue generation failed for $repo"
        continue
    fi

    # Step 4: Generate agent trajectories using SWE-agent
    # NOTE: SWE-agent must be installed separately: pip install sweagent
    # Uncomment and configure the following when ready:
    echo ""
    echo "[Step 4/6] Generating agent trajectories..."
    # Remember to set CLAUDE_API_KEY or CLAUDE_API_KEY_ROTATION environment variable
    if ! sweagent run-batch --num_workers $NUM_WORKERS \
        --instances.deployment.docker_args=--memory=10g \
        --config agent/swesmith_gen_glm.yaml \
        --instances.path logs/task_insts/$repo.json \
        --output_dir trajectories/swesmith_gen__glm__$repo \
        --random_delay_multiplier=1 \
        --agent.model.temperature 0.0; then
        echo "❌ Step 4 failed: Agent trajectory generation failed for $repo"
        continue
    fi

    # Step 5: Evaluate generated trajectories
    echo ""
    echo "[Step 5/6] Running evaluation (evaluating generated trajectories)..."
    if ! python -m swesmith.harness.eval \
        --dataset_path logs/task_insts/$repo.json \
        --predictions_path trajectories/swesmith_gen__glm__$repo/preds.json \
        --run_id swesmith_gen__glm__$repo \
        --workers $NUM_WORKERS; then
        echo "❌ Step 5 failed: Evaluation of generated trajectories failed for $repo"
        continue
    fi

    # Step 6: Collect trajectories for SFT
    echo ""
    echo "[Step 6/6] Collecting trajectories for SFT..."
    if ! python -m swesmith.train.traj_mgr.collect_trajs \
        --traj_dir trajectories/swesmith_gen__glm__$repo \
        --eval_dir logs/run_evaluation/swesmith_gen__glm__$repo \
        --workers $NUM_WORKERS; then
        echo "❌ Step 6 failed: Trajectory collection failed for $repo"
        continue
    fi

    echo ""
    echo "===================================="
    echo "Pipeline Complete for $repo!"
    echo "===================================="
    echo ""
done
