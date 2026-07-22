FROM python:3.12.8-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml ./
RUN pip install --upgrade pip==24.3.1 && pip install ".[dev]"

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY docker/backend/entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh && chown -R app:app /app

USER app

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
