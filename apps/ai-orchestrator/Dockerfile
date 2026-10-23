# MCore ai-orchestrator — Python FastAPI container
FROM python:3.12-slim

WORKDIR /app

# Layer cache: deps first
RUN pip install --no-cache-dir pyyaml fastapi uvicorn

# Source — context is apps/ai-orchestrator/, .dockerignore here applies
COPY . /app/

# Non-root user (container security hygiene)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080
CMD ["uvicorn", "main_api:app", "--host", "0.0.0.0", "--port", "8080"]
