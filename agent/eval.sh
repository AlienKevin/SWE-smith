cd SWE-bench/

source .venv/bin/activate

# --predictions_path ../SWE-agent/trajectories/ubuntu/swesmith_infer__openai--SWE-bench--SWE-agent-LM-32B__t-0.00__p-1.00__c-0.00___swe_bench_multilingual_rust/preds.json \
# --run_id multilingual_rust_eval
# --modal true >> eval_swebench_multilingual_rust.log 2>&1

# --predictions_path ../SWE-agent/trajectories/ubuntu/swesmith_infer__openai--Qwen--Qwen2.5-Coder-32B-Instruct__t-0.00__p-1.00__c-0.00___swe_bench_multilingual_rust/preds.json \
# --run_id multilingual_rust_eval_qwen2.5-coder-32b-instruct \
# --modal true >> eval_swebench_multilingual_rust_qwen2.5-coder-32b-instruct.log 2>&1

# --predictions_path ../SWE-agent/trajectories/ubuntu/swesmith_infer__openai--SWE-agent-LM-32B-Rust-gpt-91-epoch-0__t-0.00__p-1.00__c-0.00___swe_bench_multilingual_rust/preds.json \
# --run_id multilingual_rust_eval_swe_agent_lm_32b_rust_gpt_91_epoch_0 \
# --modal true >> eval_swebench_multilingual_rust_swe_agent_lm_32b_rust_gpt_91_epoch_0.log 2>&1

uv run python -m swebench.harness.run_evaluation \
    --dataset_name AlienKevin/SWE-bench_Multilingual \
    --predictions_path ../SWE-agent/trajectories/ubuntu/swesmith_infer__openai--SWE-agent-LM-32B-Rust-glm-142-epoch-2__t-0.00__p-1.00__c-0.00___swe_bench_multilingual_rust/preds.json \
    --split rust \
    --max_workers 50 \
    --run_id multilingual_rust_eval_swe_agent_lm_32b_rust_glm_142_epoch_2 \
    --modal true >> eval_swebench_multilingual_rust_swe_agent_lm_32b_rust_glm_142_epoch_2.log 2>&1
