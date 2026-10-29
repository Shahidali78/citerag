FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY backend/requirements.txt backend/requirements.lock.txt ./
RUN pip install --upgrade 'pip>=26.2,<27' && pip install -r requirements.txt -c requirements.lock.txt && useradd --uid 10001 --create-home appuser
COPY --chown=appuser:appuser backend/app ./app
COPY --chown=appuser:appuser backend/evals/sample.jsonl backend/evals/sample.md backend/evals/operations.txt backend/evals/verification.pdf ./evals/
COPY --chown=appuser:appuser backend/evals/heldout ./evals/heldout
COPY --chown=appuser:appuser docs/heldout/v1/answers-*.json /docs/heldout/v1/
COPY --chown=appuser:appuser docs/baseline/openai-evaluation.json /docs/baseline/openai-evaluation.json
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8000')+'/health', timeout=4)"
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --no-access-log"]
