FROM python:3.11-slim
LABEL maintainer="farovon" description="Limit Service — контроль лимитов Б24" version="1.2.0"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p /data /app/logs && chmod 777 /data /app/logs
RUN useradd -r -u 1001 -s /bin/false appuser && chown -R appuser:appuser /app /data
USER appuser
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1", "--access-log"]
