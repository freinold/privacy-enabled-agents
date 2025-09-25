# Use a full image with uv pre-installed as builder
FROM ghcr.io/astral-sh/uv:python3.13-bookworm@sha256:6577846cd7c2ff6821c860d2f298773b7d8c609ed3c78b147e8a3dbe45038a1e AS builder

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the transitive dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-dev --locked --no-install-project

COPY . /app

# Install the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --locked

# Use slim image as runner
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim@sha256:c4a67221d74ad160ddf4e114804bda0f8dd2d2e1aa5c16e0817cf8530ff8f5f6 AS runner

# Metadata for the image
ARG IMAGE_CREATED="unknown"
ARG IMAGE_REVISION="unknown"
ARG IMAGE_VERSION="unknown"
LABEL org.opencontainers.image.authors='Fabian Reinold <contact@freinold.eu>' \
    org.opencontainers.image.vendor='Fabian Reinold' \
    org.opencontainers.image.created="$IMAGE_CREATED" \
    org.opencontainers.image.revision="$IMAGE_REVISION" \
    org.opencontainers.image.version="$IMAGE_VERSION" \
    org.opencontainers.image.url='https://ghcr.io/freinold/privacy-enabled-agents' \
    org.opencontainers.image.documentation='https://github.com/freinold/privacy-enabled-agents/README.md' \
    org.opencontainers.image.source='https://github.com/freinold/privacy-enabled-agents' \
    org.opencontainers.image.licenses='MIT' \
    org.opencontainers.image.title='gliner-api' \
    org.opencontainers.image.description='Easily configurable API & frontend providing simple access to dynamic NER models; this image is built for CPU only.'

# Install the project into `/app`
WORKDIR /app

# Create a non-root user and group with UID/GID 1001
RUN groupadd -g 1001 appuser && \
    useradd -m -u 1001 -g appuser appuser

# Copy the application files from the builder stage
COPY --from=builder --chown=appuser:appuser /app /app

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Disable tqdm for cleaner logs
ENV TQDM_DISABLE=1
ENV HF_HUB_DISABLE_PROGRESS_BARS=1

# Disable python warnings
ENV PYTHONWARNINGS="ignore"

# Switch to non-root user
USER appuser

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT ["python", "main.py"]