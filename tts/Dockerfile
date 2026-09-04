FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime

# Install system dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code and voice assets
COPY server.py .
COPY voices/ ./voices/

# Expose API port (5000) and Gradio Web UI port (7860)
EXPOSE 5000 7860

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV VOICES_DIR=/app/voices
ENV PORT=5000

CMD ["python", "server.py"]
