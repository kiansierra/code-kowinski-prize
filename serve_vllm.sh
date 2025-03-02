# unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF
# deepseek-ai/DeepSeek-R1-Distill-Qwen-7B
# serve unsloth/DeepSeek-R1-Distill-Qwen-1.5B-unsloth-bnb-4bit
vllm serve deepseek-ai/DeepSeek-R1-Distill-Qwen-7B\
 --port 8000\
 --host 0.0.0.0\
 --dtype half\
 --max-model-len 81920\
 --max-num-seqs 128\
 --trust-remote-code\
 --tensor-parallel-size 2\
 --gpu-memory-utilization 0.95\
 --seed 2024\
 --quantization bitsandbytes\
 --load-format bitsandbytes\
 --kv-cache-dtype auto