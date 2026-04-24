FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy application code
COPY app.py /app/app.py

# Create non-root user
RUN useradd -u 1001 -m app && chown -R app:app /app

# Switch to non-root user
USER app

# Port from environment
ENV PORT=8080
EXPOSE 8080

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz').read()" || exit 1

CMD ["python", "app.py"]
