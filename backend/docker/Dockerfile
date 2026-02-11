# Base image
FROM ubuntu:22.04

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive

# Update & install core tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    nasm \
    build-essential \
    gdb \
    python3 \
    python3-pip \
    nano \
    vim \
    curl \
    wget \
    git \
    make \
    jq \
    net-tools \
    iputils-ping \
    strace \
    lsof \
    && apt clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app
RUN mkdir -p /app/scripts /work



# Copy your local scripts into the container
COPY sandbox_scripts/run_pipeline.sh /app/scripts/run_pipeline.sh
COPY sandbox_scripts/parse_registers_multiline.py /app/scripts/parse_registers_multiline.py

# Give execute permissions
RUN chmod +x /app/scripts/run_pipeline.sh

# Optional: Add a non-root user for safer sandboxing
# Optional: Add a non-root user for safer sandboxing
RUN useradd -ms /bin/bash slaituser \
    && chown -R slaituser:slaituser /app /work

# Switch to non-root user
USER slaituser


WORKDIR /work
CMD ["/bin/bash"]
