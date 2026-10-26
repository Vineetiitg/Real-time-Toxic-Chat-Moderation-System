"""
Deploy SafeChat ML Microservice to Hugging Face Spaces: vineet88/safechat-ml-service
"""

import os
import shutil
import tempfile
from huggingface_hub import HfApi

REPO_ID = "vineet88/safechat-ml-service"
REPO_TYPE = "space"

print(f"Preparing deployment payload for Hugging Face Space: {REPO_ID}...")

# Create staging directory
with tempfile.TemporaryDirectory() as staging_dir:
    print(f"Staging files in temporary directory: {staging_dir}")

    # 1. Copy app directory
    app_dest = os.path.join(staging_dir, "app")
    shutil.copytree(
        "ml-service/app",
        app_dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    )

    # 2. Copy detoxification directory
    detox_dest = os.path.join(staging_dir, "detoxification")
    shutil.copytree(
        "detoxification",
        detox_dest,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    )

    # 3. Create requirements.txt
    requirements_content = """# --- Core ML ---
torch>=2.1.0 --extra-index-url https://download.pytorch.org/whl/cpu
transformers>=4.36.0
tokenizers>=0.15.0
accelerate>=0.25.0
sentencepiece>=0.1.99
protobuf>=4.25.3

# --- FastAPI & Async Server ---
fastapi>=0.109.0
uvicorn[standard]>=0.25.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
websockets>=12.0

# --- LLM Client & Detoxification ---
google-genai>=1.0.0
httpx>=0.26.0

# --- Text & Language Processing ---
langdetect>=1.0.9
regex>=2023.12.25
emoji>=2.9.0
numpy>=1.24.0

# --- Database & Utilities ---
motor>=3.3.2
pymongo>=4.6.1
loguru>=0.7.2
python-dotenv>=1.0.0
"""
    with open(os.path.join(staging_dir, "requirements.txt"), "w", encoding="utf-8") as f:
        f.write(requirements_content)

    # 4. Create Dockerfile
    dockerfile_content = """FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_NO_CACHE_DIR=1 \\
    HF_HOME=/tmp/huggingface \\
    TRANSFORMERS_CACHE=/tmp/huggingface/hub \\
    CLASSIFIER_MODEL=vineet88/hingbert-toxicity-finetuned \\
    SAFECHAT_CLASSIFIER_MODEL=vineet88/hingbert-toxicity-finetuned \\
    HOST=0.0.0.0 \\
    PORT=8000 \\
    SAFECHAT_HOST=0.0.0.0 \\
    SAFECHAT_PORT=8000 \\
    PYTHONPATH="/app:/app/detoxification"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy application and detoxification code
COPY app ./app
COPY detoxification ./detoxification

# Create cache and models directory with open permissions for HF non-root user
RUN mkdir -p /app/checkpoints /app/models /tmp/huggingface && chmod -R 777 /app /tmp/huggingface

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/api/v1/health'); exit(0 if r.status_code == 200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
"""
    with open(os.path.join(staging_dir, "Dockerfile"), "w", encoding="utf-8") as f:
        f.write(dockerfile_content)

    # 5. Create Space README.md (Frontmatter for Docker SDK)
    readme_content = """---
title: SafeChat ML Service
emoji: 🛡️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 8000
pinned: false
---

# SafeChat ML Service — High-Throughput Toxicity Inference API

Production FastAPI microservice powering real-time multilingual toxicity classification and intent-preserving detoxification.
Built with fine-tuned Hing-RoBERTa (`vineet88/hingbert-toxicity-finetuned`) and Gemini 2.5 Flash contextual arbitration.

## Interactive Endpoints:
- `GET /` — Service metadata & system health
- `GET /docs` — Interactive OpenAPI Swagger UI
- `POST /api/v1/moderate` — Real-time 6-tag toxicity classification & arbitration
- `POST /api/v1/detoxify` — Intent-preserving polite style transfer
- `WS /ws/moderate` — Real-time streaming WebSocket
"""
    with open(os.path.join(staging_dir, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)

    # 6. Create .dockerignore
    dockerignore_content = """__pycache__
*.pyc
*.pyo
*.pyd
.git
.github
.env
.venv
checkpoints
"""
    with open(os.path.join(staging_dir, ".dockerignore"), "w", encoding="utf-8") as f:
        f.write(dockerignore_content)

    print("Uploading staged files to Hugging Face Space...")
    api = HfApi()
    api.upload_folder(
        folder_path=staging_dir,
        repo_id=REPO_ID,
        repo_type=REPO_TYPE,
        commit_message="deploy: upgrade ML service to Hing-RoBERTa, SentencePiece, and Gemini arbitration",
    )
    print("Deployment completed successfully!")
