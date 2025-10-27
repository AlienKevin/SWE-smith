#!/bin/bash

set -e  # Exit on error

# On macOS, need to set DOCKER_HOST, otherwise docker APIClient will fail
export DOCKER_HOST=unix://$HOME/.docker/run/docker.sock

# Clean up stale containers from previous run
docker ps -a | grep swesmith.val | awk '{print $1}' | xargs docker rm -f 2>/dev/null || true

REPO_NAME="${1:-iamkun/dayjs}"
MAX_BUGS="${2:-100}"

# Function to get repo info from registry
get_repo_info() {
    local repo_name="$1"
    python3 -c "
import sys
sys.path.append('.')
from swesmith.profiles import registry

repo_name = '$repo_name'
for name, profile_class in registry.data.items():
    if hasattr(profile_class, 'owner') and hasattr(profile_class, 'repo'):
        if f\"{profile_class.owner}/{profile_class.repo}\" == repo_name:
            # Create instance to access properties
            instance = profile_class()
            print(f\"{profile_class.owner}__{profile_class.repo}.{profile_class.commit[:8]}|{instance.image_name}\")
            sys.exit(0)
print('REPO_NOT_FOUND', file=sys.stderr)
sys.exit(1)
"
}

# Get repository information
echo "Looking up repository: $REPO_NAME"
REPO_INFO=$(get_repo_info "$REPO_NAME" 2>/dev/null) || {
    echo "Error: Repository '$REPO_NAME' not found in registry."
    echo "Available JavaScript repositories:"
    python3 -c "
import sys
sys.path.append('.')
from swesmith.profiles import registry
for name, profile_class in registry.data.items():
    if hasattr(profile_class, 'owner') and hasattr(profile_class, 'repo'):
        print(f\"  {profile_class.owner}/{profile_class.repo}\")
" | sort | uniq
    exit 1
}

REPO_ID=$(echo "$REPO_INFO" | cut -d'|' -f1)
DOCKER_IMAGE=$(echo "$REPO_INFO" | cut -d'|' -f2)

echo "=========================================="
echo "Procedural Bug Generation for SWE-smith"
echo "=========================================="
echo "Repository: $REPO_NAME"
echo "Repository ID: $REPO_ID"
echo "Max bugs per modifier: $MAX_BUGS"
echo "Docker image: $DOCKER_IMAGE"
echo "=========================================="
echo ""

echo "[Step 1/4] Verifying Docker image..."
if docker image inspect "$DOCKER_IMAGE" > /dev/null 2>&1; then
    echo "✓ Docker image found: $DOCKER_IMAGE"
else
    echo "✗ Docker image not found: $DOCKER_IMAGE"
    echo "Attempting to pull the image..."
    docker pull "$DOCKER_IMAGE" || {
        echo "Error: Failed to pull Docker image. Please ensure the image exists."
        exit 1
    }
fi
echo ""

echo "[Step 2/4] Generating bugs procedurally..."
echo "Running: python -m swesmith.bug_gen.procedural.generate $REPO_ID --max_bugs $MAX_BUGS"
python -m swesmith.bug_gen.procedural.generate "$REPO_ID" --max_bugs "$MAX_BUGS" || {
    echo "Error: Bug generation failed."
    exit 1
}
echo ""

echo "[Step 3/4] Collecting all patches..."
PATCHES_FILE="logs/bug_gen/${REPO_ID}_all_patches.json"
echo "Running: python -m swesmith.bug_gen.collect_patches logs/bug_gen/$REPO_ID"
python -m swesmith.bug_gen.collect_patches "logs/bug_gen/$REPO_ID" || {
    echo "Error: Patch collection failed."
    exit 1
}

if [ -f "$PATCHES_FILE" ]; then
    NUM_PATCHES=$(jq length "$PATCHES_FILE")
    echo "✓ Collected $NUM_PATCHES patches to $PATCHES_FILE"
else
    echo "✗ Patches file not found: $PATCHES_FILE"
    exit 1
fi
echo ""

 # Determine number of CPU cores for parallel validation
 if command -v nproc >/dev/null 2>&1; then
     NUM_CORES=$(nproc)
 elif command -v sysctl >/dev/null 2>&1; then
     NUM_CORES=$(sysctl -n hw.ncpu || echo 8)
 else
     NUM_CORES=8
 fi

echo "[Step 4/4] Running validation..."
echo "Running: python -m swesmith.harness.valid $PATCHES_FILE -w $NUM_CORES"
python -m swesmith.harness.valid "$PATCHES_FILE" -w "$NUM_CORES" || {
    echo "Warning: Validation encountered errors but may have partial results."
}
echo ""

echo "=========================================="
echo "Bug Generation Complete!"
echo "=========================================="
echo "Generated patches: $PATCHES_FILE"
echo "Validation results: logs/run_validation/$REPO_ID/"
echo ""
echo "Next steps:"
echo "  1. Review validation results in logs/run_validation/$REPO_ID/"
echo "  2. Analyze bugs with: python scripts/analyze_bugs.py $REPO_ID"
echo "  3. Collect validated instances: python -m swesmith.harness.gather logs/run_validation/$REPO_ID"
echo "=========================================="