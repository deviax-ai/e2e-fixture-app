# Deliberately minimal — kept this way so Deviax's issue_detection has
# things to flag (no USER directive, no HEALTHCHECK, root by default).
# The QA test answers the resulting IssueCards with canned values.
FROM python:3.12-slim
WORKDIR /app
COPY app.py /app/app.py
RUN useradd -u 1001 -m app && chown -R app:app /app
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz').read()" || exit 1
CMD ["python", "app.py"]
