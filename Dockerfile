FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY detoxification ./detoxification
COPY frontend/dist ./frontend/dist

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir loguru aiosqlite greenlet bcrypt && \
    pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "safety_platform.main:app", "--host", "0.0.0.0", "--port", "8000"]
