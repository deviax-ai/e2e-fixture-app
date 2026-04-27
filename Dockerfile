FROM python:3.12-slim

# Security: run as non-root user
RUN useradd -u 1001 -m app

WORKDIR /app

# Copy application code
COPY --chown=app:app app.py /app/app.py

# Switch to non-root user
USER app

# Expose port (configurable via PORT env var)
EXPOSE 8080

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz').read()" || exit 1

CMD ["python", "app.py"]
