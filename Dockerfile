# Deliberately minimal — kept this way so Deviax's issue_detection has
# things to flag (no USER directive, no HEALTHCHECK, root by default).
# The QA test answers the resulting IssueCards with canned values.
FROM python:3.12-slim
WORKDIR /app

# Create non-root user
RUN adduser --system --uid 1001 --group appuser

COPY app.py /app/app.py

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz').read()"

CMD ["python", "app.py"]
