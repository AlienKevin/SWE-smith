for dir in logs/bug_gen/*/; do
    if [ -d "$dir" ]; then
        echo "Processing $dir..."
        uv run python -m swesmith.bug_gen.combine.same_file "$dir" --num_patches 2 \
          --limit_per_file 9999999999 \
          --max_combos 9999999999
        uv run python -m swesmith.bug_gen.combine.same_file "$dir" --num_patches 3 \
          --limit_per_file 9999999999 \
          --max_combos 9999999999
        uv run python -m swesmith.bug_gen.combine.same_module "$dir" --num_patches 2 \
          --limit_per_module 9999999999 \
          --max_combos 9999999999 \
          --depth 2
        uv run python -m swesmith.bug_gen.combine.same_module "$dir" --num_patches 3 \
          --limit_per_module 9999999999 \
          --max_combos 9999999999 \
          --depth 2
    fi
done
