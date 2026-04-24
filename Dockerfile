FROM python:3.12-slim
WORKDIR /app
COPY app.py .
RUN useradd -u 1001 -m app && chown -R app:app /app
USER app
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import http.client; c=http.client.HTTPConnection('localhost',8080); c.request('GET','/healthz'); r=c.getresponse(); exit(0 if r.status==200 else 1)"
CMD ["python", "app.py"]
