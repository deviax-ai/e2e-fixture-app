FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

FROM base AS runtime
COPY app.py .
RUN useradd -u 1001 -m app && \
    chown -R app:app /app && \
    mkdir -p /data && \
    chown app:app /data
USER app
EXPOSE 8080
CMD ["python", "app.py"]
