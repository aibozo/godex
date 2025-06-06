# Minimal container to run tools if Firejail is unavailable.
FROM python:3.12-slim

# Install only what's needed by default: grep, python packages (if any tool requires)
RUN apt-get update && apt-get install -y --no-install-recommends \
        grep \
        git \
        patch \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user to avoid running as root inside container
RUN useradd -m agentuser
USER agentuser
WORKDIR /home/agentuser

# Entrypoint: we will mount the host repo at /workspace inside Docker.
ENTRYPOINT ["tail", "-f", "/dev/null"]