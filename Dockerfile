FROM python:3.12-slim
WORKDIR /app
COPY app.py /app/app.py
RUN useradd -u 1001 -m app && chown -R app:app /app
USER app
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz', timeout=2).read()"
CMD ["python", "app.py"]
