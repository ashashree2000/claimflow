# ClaimFlow API image. Build: docker build -t claimflow-api .
# Run:  docker run --rm -p 8000:8000 --env-file .env claimflow-api   (the key is never baked into the image)
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt
COPY claimflow/ claimflow/
COPY api/ api/
COPY data/policies data/policies
COPY data/sops data/sops
COPY eval/results.json eval/results.json
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
