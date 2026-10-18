FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    STOCKPILOT_INSTANCE=/data \
    DATABASE_URL=sqlite:////data/inventory.db \
    MODEL_DIR=/data/models \
    UPLOAD_FOLDER=/data/uploads \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN groupadd --gid 10001 stockpilot && useradd --uid 10001 --gid stockpilot --no-create-home stockpilot \
    && mkdir -p /data/models /data/uploads && chown -R stockpilot:stockpilot /data /app
USER stockpilot
EXPOSE 5000
HEALTHCHECK --interval=15s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health',timeout=2)"
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--timeout", "60", "app:create_app()"]
