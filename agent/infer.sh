curl https://swe-b--example-vllm-inference-serve.modal.run/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "SWE-agent-LM-32B-Rust-glm-142-epoch-2",
    "messages": [
      { "role": "user", "content": "Hi!" }
    ]
  }'

time uv run sweagent run-batch --config agent/swesmith_infer.yaml >> swebench_multilingual_rust_swe_agent_lm_32b_rust_glm_142_epoch_2.log 2>&1
