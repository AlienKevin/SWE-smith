cd SWE-bench/

source .venv/bin/activate

uv run python -m swebench.harness.run_evaluation \
    --dataset_name AlienKevin/SWE-bench_Multilingual \
    --predictions_path ../SWE-agent/trajectories/ubuntu/swesmith_infer__openai--SWE-bench--SWE-agent-LM-32B__t-0.00__p-1.00__c-0.00___swe_bench_multilingual_rust/preds.json \
    --split rust \
    --max_workers 50 \
    --run_id multilingual_rust_eval \
    --modal true >> eval_swebench_multilingual_rust.log 2>&1
