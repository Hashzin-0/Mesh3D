FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV BLENDER_BIN=/usr/bin/blender
ENV MESH3D_BLENDER_DATA_DIR=/data
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    blender ffmpeg ca-certificates tini \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py ./app.py
RUN useradd --create-home --uid 10002 blenderworker \
    && mkdir -p /data/jobs /tmp/blender \
    && chown -R blenderworker:blenderworker /app /data /tmp/blender
USER blenderworker
EXPOSE 8080
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
