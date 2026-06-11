FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS production
RUN groupadd --system app && useradd --system --gid app app

COPY --chown=app:app src/ ./src/
COPY --chown=app:app dags/ ./dags/
COPY --chown=app:app schemas/ ./schemas/
COPY --chown=app:app sql/ ./sql/
COPY --chown=app:app transform/ ./transform/
COPY --chown=app:app etl_pipeline.py .
COPY --chown=app:app generate_dataset.py .
COPY --chown=app:app .env.example .

USER app
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

CMD ["python", "etl_pipeline.py"]

FROM base AS development
RUN groupadd --system app && useradd --system --gid app app

COPY --chown=app:app src/ ./src/
COPY --chown=app:app dags/ ./dags/
COPY --chown=app:app schemas/ ./schemas/
COPY --chown=app:app sql/ ./sql/
COPY --chown=app:app transform/ ./transform/
COPY --chown=app:app etl_pipeline.py .
COPY --chown=app:app generate_dataset.py .
COPY --chown=app:app .env.example .

RUN pip install --no-cache-dir pytest pytest-cov

USER app
CMD ["python", "-m", "pytest", "tests/"]
