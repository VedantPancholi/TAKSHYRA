FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml ./
COPY takshyra ./takshyra
RUN pip install --no-cache-dir .
COPY alembic.ini ./
COPY migrations ./migrations
COPY seed ./seed
COPY scripts/smoke.py ./scripts/smoke.py
EXPOSE 8000
