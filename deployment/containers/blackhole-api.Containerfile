FROM python:3.12.11-slim-bookworm

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10002 fa3api \
    && useradd --uid 10002 --gid 10002 --create-home --home-dir /home/fa3api --shell /usr/sbin/nologin fa3api \
    && mkdir -p /opt/fa3/app /opt/fa3/src /var/lib/fa3/audit /data/raw /data/processed /run/fa3/hrb-leases \
    && chown -R 10002:10002 /var/lib/fa3/audit /data/processed /home/fa3api

WORKDIR /opt/fa3

COPY apps/blackhole-api/requirements.lock /tmp/requirements.lock
RUN python -m pip install --disable-pip-version-check --no-cache-dir -r /tmp/requirements.lock \
    && python -m pip check

COPY src/ /opt/fa3/src/
COPY apps/blackhole-api/main.py /opt/fa3/app/main.py

ENV PYTHONPATH=/opt/fa3/src \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FA3_INPUT_ROOT=/data/raw \
    FA3_OUTPUT_ROOT=/data/processed \
    FA3_HRB_LEASE_ROOT=/run/fa3/hrb-leases \
    FA3_AUDIT_LOG=/var/lib/fa3/audit/blackhole-api.jsonl \
    FA3_FFMPEG_BIN=ffmpeg \
    FA3_FFPROBE_BIN=ffprobe

LABEL io.fa3.profile="FA3-BLACKHOLE-API-001" \
      io.fa3.runtime.class="REFERENCE_OCI_NOT_PRODUCTION" \
      io.fa3.zero-copy-claimed="false"

USER 10002:10002
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2).read()" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
