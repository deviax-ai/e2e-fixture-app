# Deliberately minimal — kept this way so Deviax's issue_detection has
# things to flag (no USER directive, no HEALTHCHECK, root by default).
# The QA test answers the resulting IssueCards with canned values.
FROM python:3.12-slim
WORKDIR /app
COPY app.py /app/app.py
EXPOSE 8080
CMD ["python", "app.py"]
