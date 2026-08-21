FROM vllm/vllm-openai:latest

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install bitsandbytes for 4-bit quantized loading
RUN pip install --no-cache-dir bitsandbytes
