FROM vllm/vllm-openai:latest

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# ONLY upgrade vLLM (it will pull correct transformers)
RUN pip install --upgrade git+https://github.com/vllm-project/vllm.git
