FROM vllm/vllm-openai:latest

# Install FlashInfer
RUN pip install --upgrade \
    git+https://github.com/huggingface/transformers.git \
    git+https://github.com/vllm-project/vllm.git
