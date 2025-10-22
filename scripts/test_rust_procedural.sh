#!/bin/bash


set -e  # Exit on error

MAX_BUGS="${1:-50}"  # Default to 50 bugs per modifier per repo

echo "=========================================="
echo "Rust Procedural Bug Generation Testing"
echo "=========================================="
echo "Max bugs per modifier per repo: $MAX_BUGS"
echo "=========================================="
echo ""

RUST_PROFILES=(
    "dtolnay/anyhow:1d7ef1db"
    "marshallpierce/rust-base64:cac5ff84"
    "clap-rs/clap:3716f9f4"
    "hyperium/hyper:c88df788"
    "rust-itertools/itertools:041c733c"
    "serde-rs/json:cd55b5a0"
    "rust-lang/log:3aa1359e"
    "dtolnay/semver:37bcbe69"
    "tokio-rs/tokio:ab3ff69c"
    "uuid-rs/uuid:2fd9b614"
    "rust-lang/mdBook:37273ba8"
    "BurntSushi/rust-csv:da000888"
    "servo/html5ever:b93afc94"
    "BurntSushi/byteorder:5a82625f"
    "chronotope/chrono:d43108cb"
    "orium/rpds:3e7c8ae6"
    "rayon-rs/rayon:1fd20485"
    "BurntSushi/ripgrep:3b7fd442"
    "rust-lang/rust-clippy:f4f579f4"
)

TOTAL_PROFILES=${#RUST_PROFILES[@]}
CURRENT=0
SUCCESSFUL=0
FAILED=0
FAILED_PROFILES=()

mkdir -p logs/rust_testing

for PROFILE in "${RUST_PROFILES[@]}"; do
    CURRENT=$((CURRENT + 1))
    
    REPO_NAME=$(echo "$PROFILE" | cut -d':' -f1)
    COMMIT_SHORT=$(echo "$PROFILE" | cut -d':' -f2)
    REPO_OWNER=$(echo "$REPO_NAME" | cut -d'/' -f1)
    REPO_NAME_ONLY=$(echo "$REPO_NAME" | cut -d'/' -f2)
    REPO_ID="${REPO_OWNER}__${REPO_NAME_ONLY}.${COMMIT_SHORT}"
    
    echo ""
    echo "=========================================="
    echo "[$CURRENT/$TOTAL_PROFILES] Testing: $REPO_NAME"
    echo "Repository ID: $REPO_ID"
    echo "=========================================="
    
    LOG_FILE="logs/rust_testing/${REPO_ID}.log"
    
    {
        echo "Starting bug generation for $REPO_ID at $(date)"
        
        echo "[Step 1/3] Generating bugs procedurally..."
        if python -m swesmith.bug_gen.procedural.generate "$REPO_ID" --max_bugs "$MAX_BUGS" 2>&1; then
            echo "✓ Bug generation completed"
        else
            echo "✗ Bug generation failed"
            exit 1
        fi
        
        echo "[Step 2/3] Collecting all patches..."
        PATCHES_FILE="logs/bug_gen/${REPO_ID}_all_patches.json"
        if python -m swesmith.bug_gen.collect_patches "logs/bug_gen/$REPO_ID" 2>&1; then
            if [ -f "$PATCHES_FILE" ]; then
                NUM_PATCHES=$(jq length "$PATCHES_FILE" 2>/dev/null || echo "unknown")
                echo "✓ Collected $NUM_PATCHES patches to $PATCHES_FILE"
            else
                echo "✗ Patches file not found: $PATCHES_FILE"
                exit 1
            fi
        else
            echo "✗ Patch collection failed"
            exit 1
        fi
        
        echo "[Step 3/3] Running validation..."
        if python -m swesmith.harness.valid "$PATCHES_FILE" 2>&1; then
            echo "✓ Validation completed"
        else
            echo "⚠ Validation completed with warnings"
        fi
        
        echo "Completed testing for $REPO_ID at $(date)"
        
    } > "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        SUCCESSFUL=$((SUCCESSFUL + 1))
        echo "✓ SUCCESS: $REPO_NAME"
    else
        FAILED=$((FAILED + 1))
        FAILED_PROFILES+=("$REPO_NAME")
        echo "✗ FAILED: $REPO_NAME (see $LOG_FILE)"
    fi
    
    echo "Progress: $SUCCESSFUL successful, $FAILED failed out of $CURRENT tested"
done

echo ""
echo "=========================================="
echo "Testing Complete!"
echo "=========================================="
echo "Total profiles tested: $TOTAL_PROFILES"
echo "Successful: $SUCCESSFUL"
echo "Failed: $FAILED"

if [ $FAILED -gt 0 ]; then
    echo ""
    echo "Failed profiles:"
    for PROFILE in "${FAILED_PROFILES[@]}"; do
        echo "  - $PROFILE"
    done
fi

echo ""
echo "Logs saved to: logs/rust_testing/"
echo ""
echo "Next steps:"
echo "  1. Analyze each profile: python scripts/analyze_bugs.py <repo_id>"
echo "  2. Generate comprehensive report: python scripts/analyze_rust_comprehensive.py"
echo "=========================================="
