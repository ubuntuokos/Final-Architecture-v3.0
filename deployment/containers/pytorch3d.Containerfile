# Build with immutable OCI refs only, for example:
#   --build-arg BUILDER_BASE=registry/repo@sha256:<64hex>
#   --build-arg RUNTIME_BASE=registry/repo@sha256:<64hex>
# The qualification worker must provide pytorch3d-source.tar and bind its
# SOURCE_SHA256 to PYTORCH3D_COMMIT in the signed qualification receipt.
ARG BUILDER_BASE
ARG RUNTIME_BASE
FROM ${BUILDER_BASE} AS builder
ARG BUILDER_BASE
ARG PYTORCH3D_COMMIT=0a7d4c1a171e8b768c63f15b17564f9ad495f49b
ARG SOURCE_SHA256
RUN case "$BUILDER_BASE" in *@sha256:[0-9a-f][0-9a-f]*) ;; *) echo "BUILDER_BASE must be digest-pinned" >&2; exit 2 ;; esac
RUN test -n "$SOURCE_SHA256"
WORKDIR /build
COPY pytorch3d-source.tar /build/pytorch3d-source.tar
RUN echo "$SOURCE_SHA256  /build/pytorch3d-source.tar" | sha256sum -c -
RUN mkdir /build/pytorch3d \
    && tar -xf /build/pytorch3d-source.tar -C /build/pytorch3d --strip-components=1
RUN python -m venv /opt/build-venv
ENV PATH=/opt/build-venv/bin:$PATH
WORKDIR /build/pytorch3d
RUN python -m pip install --upgrade pip build \
    && python -m build --wheel --no-isolation \
    && sha256sum dist/*.whl > /build/wheel.sha256 \
    && printf '%s\n%s\n' "$PYTORCH3D_COMMIT" "$SOURCE_SHA256" > /build/source-identity.txt

FROM ${RUNTIME_BASE} AS runtime
ARG RUNTIME_BASE
ARG PYTORCH3D_COMMIT=0a7d4c1a171e8b768c63f15b17564f9ad495f49b
RUN case "$RUNTIME_BASE" in *@sha256:[0-9a-f][0-9a-f]*) ;; *) echo "RUNTIME_BASE must be digest-pinned" >&2; exit 2 ;; esac
LABEL org.fa3.provider="FA3-PROVIDER-PYTORCH3D-001" \
      org.fa3.source.revision="${PYTORCH3D_COMMIT}"
USER root
COPY --from=builder /build/pytorch3d/dist/*.whl /tmp/pytorch3d.whl
COPY --from=builder /build/wheel.sha256 /usr/share/fa3/pytorch3d-wheel.sha256
COPY --from=builder /build/source-identity.txt /usr/share/fa3/pytorch3d-source-identity.txt
RUN python -m pip install --no-cache-dir --no-index /tmp/pytorch3d.whl && rm -f /tmp/pytorch3d.whl
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin fa3worker
USER 10001:10001
WORKDIR /work
ENV PYTHONNOUSERSITE=1
ENTRYPOINT ["python", "-c", "import pytorch3d; print(pytorch3d.__file__)"]
