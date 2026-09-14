# Build only with an immutable base image reference:
#   podman build --build-arg BASE_IMAGE='...@sha256:...' ...
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG COMFYUI_ARCHIVE_URL
ARG COMFYUI_ARCHIVE_SHA256

USER 0
RUN test -n "${COMFYUI_ARCHIVE_URL}" && test -n "${COMFYUI_ARCHIVE_SHA256}" \
 && python3 - <<'PY'
import os, urllib.request
url=os.environ["COMFYUI_ARCHIVE_URL"]
urllib.request.urlretrieve(url, "/tmp/comfyui.tar.gz")
PY
RUN echo "${COMFYUI_ARCHIVE_SHA256}  /tmp/comfyui.tar.gz" | sha256sum -c - \
 && mkdir -p /opt/comfyui \
 && tar -xzf /tmp/comfyui.tar.gz --strip-components=1 -C /opt/comfyui \
 && rm -f /tmp/comfyui.tar.gz \
 && python3 -m pip install --no-cache-dir -r /opt/comfyui/requirements.txt \
 && useradd --create-home --uid 10001 --shell /usr/sbin/nologin fa3comfy \
 && mkdir -p /home/fa3/output /home/fa3/models \
 && chown -R 10001:10001 /opt/comfyui /home/fa3

WORKDIR /opt/comfyui
USER 10001:10001
EXPOSE 8188
ENTRYPOINT ["python3","main.py","--listen","0.0.0.0","--port","8188","--output-directory","/home/fa3/output"]
