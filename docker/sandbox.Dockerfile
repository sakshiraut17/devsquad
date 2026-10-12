# DevSquad Ephemeral Execution Sandbox
# Hardened, isolated container for running tests and syntax checks on synthesized code patches.
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install basic toolchains
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root sandbox execution user
RUN groupadd -g 1001 sandbox && \
    useradd -u 1001 -g sandbox -m -s /bin/bash sandboxuser

WORKDIR /workspace
RUN chown -R sandboxuser:sandbox /workspace

USER sandboxuser

# Default command for sandbox container
CMD ["pytest", "--version"]
