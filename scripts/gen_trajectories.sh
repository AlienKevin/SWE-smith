#!/bin/bash

repo="dtolnay__anyhow.1d7ef1db"

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
echo "[Step 0/5] Creating mirror repository..."
python -c "from swesmith.profiles import registry; registry.get('$repo').create_mirror()"
echo "✓ Mirror repository ready"

# Step 1: Collect task instances with 1+ Fail-to-Pass tests
echo ""
echo "[Step 1/5] Gathering validated task instances..."
python -m swesmith.harness.gather logs/run_validation/$repo --override_branch --debug_subprocess

# Step 2: Run evaluation to generate gold trajectories
echo ""
echo "[Step 2/5] Running evaluation (generating gold trajectories)..."
python -m swesmith.harness.eval \
    --dataset_path logs/task_insts/$repo.json \
    --predictions_path gold \
    --run_id $repo

# Step 3: Generate issues for the task instances
echo ""
echo "[Step 3/5] Generating issue descriptions..."
python -m swesmith.issue_gen.generate \
    --dataset_path logs/task_insts/$repo.json \
    --config_file configs/issue_gen/ig_v2.yaml \
    --workers 4 \
    --redo_existing

# Step 4: Generate agent trajectories using SWE-agent
# NOTE: SWE-agent must be installed separately: pip install sweagent
# Uncomment and configure the following when ready:
echo ""
echo "[Step 4/5] Generating agent trajectories..."
# Remember to set CLAUDE_API_KEY or CLAUDE_API_KEY_ROTATION environment variable
sweagent run-batch --num_workers 10 \
    --instances.deployment.docker_args=--memory=10g \
    --config agent/swesmith_gen_glm.yaml \
    --instances.path logs/task_insts/$repo.json \
    --output_dir trajectories/swesmith_gen__glm__$repo \
    --random_delay_multiplier=1 \
    --agent.model.temperature 0.0

echo ""
echo "===================================="
echo "Pipeline Complete!"
echo "===================================="
