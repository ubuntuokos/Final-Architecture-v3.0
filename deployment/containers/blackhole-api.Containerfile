FROM python:3.12-slim-bookworm

ARG FA3_UID=10002
ARG FA3_GID=10002

RUN groupadd --gid "${FA3_GID}" fa3api \
    && useradd --uid "${FA3_UID}" --gid "${FA3_GID}" --create-home --shell /usr/sbin/nologin fa3api \
    && install -d -o "${FA3_UID}" -g "${FA3_GID}" -m 0750 /opt/fa3 /var/lib/fa3-blackhole

WORKDIR /opt/fa3

COPY deployment/containers/blackhole-api.requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r /tmp/requirements.txt \
    && rm -f /tmp/requirements.txt

RUN install -d -o "${FA3_UID}" -g "${FA3_GID}" -m 0750 /opt/fa3/src
COPY --chown=fa3api:fa3api src/blackhole_api.py ./src/blackhole_api.py

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FA3_BLACKHOLE_DB=/var/lib/fa3-blackhole/jobs.sqlite3 \
    FA3_BLACKHOLE_TOKEN_VAULT=/run/secrets/fa3-blackhole-vault.json \
    FA3_HRB_LEASE_DIR=/run/fa3/hrb/leases \
    FA3_HRB_BIN=/usr/local/bin/fa3-host-resource-broker \
    FA3_BLACKHOLE_PRINCIPAL=FA3-MARKETING-STUDIO

USER fa3api:fa3api

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).read()"]

CMD ["python", "-m", "uvicorn", "src.blackhole_api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-server-header"]
