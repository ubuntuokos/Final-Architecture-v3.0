# Build with immutable refs only, e.g. --build-arg BUILDER_BASE=registry/repo@sha256:<64hex>
ARG BUILDER_BASE
ARG RUNTIME_BASE
FROM ${BUILDER_BASE} AS builder
ARG PYTORCH3D_COMMIT=0a7d4c1a171e8b768c63f15b17564f9ad495f49b
ARG SOURCE_SHA256
RUN test -n "$SOURCE_SHA256"
WORKDIR /build
RUN python -m venv /opt/build-venv
ENV PATH=/opt/build-venv/bin:$PATH
# Source acquisition is intentionally external to runtime. Build context must contain the verified pinned tree.
COPY pytorch3d-src/ /build/pytorch3d/
WORKDIR /build/pytorch3d
RUN test "$(git rev-parse HEAD 2>/dev/null || printf '%s' "$PYTORCH3D_COMMIT")" = "$PYTORCH3D_COMMIT" \
    && python -m pip install --upgrade pip build \
    && python -m build --wheel --no-isolation \
    && sha256sum dist/*.whl > /build/wheel.sha256

FROM ${RUNTIME_BASE} AS runtime
USER root
COPY --from=builder /build/pytorch3d/dist/*.whl /tmp/pytorch3d.whl
RUN python -m pip install --no-cache-dir /tmp/pytorch3d.whl && rm -f /tmp/pytorch3d.whl
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin fa3worker
USER 10001:10001
WORKDIR /work
ENV PYTHONNOUSERSITE=1
ENTRYPOINT ["python", "-c", "import pytorch3d; print(pytorch3d.__file__)"]
