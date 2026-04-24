FROM python:3.12-slim

# Security and optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy application code
COPY app.py /app/app.py

# Create non-root user
RUN useradd -u 1001 -m appuser && \
    chown -R appuser:appuser /app && \
    mkdir -p /tmp && \
    chown appuser:appuser /tmp

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz').read()" || exit 1

EXPOSE 8080
CMD ["python", "app.py"]
