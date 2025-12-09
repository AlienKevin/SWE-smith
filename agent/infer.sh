curl https://swe-b--example-vllm-inference-serve.modal.run/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llm",
    "messages": [
      { "role": "user", "content": "Hi!" }
    ]
  }'

time uv run sweagent run-batch --config agent/swesmith_infer.yaml >> swebench_multilingual_rust_qwen2.5-coder-32b-instruct.log 2>&1
