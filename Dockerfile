FROM nvidia/cuda:12.6.0-base-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.13 and build tools
RUN apt-get update && apt-get install -y \
    software-properties-common git wget curl build-essential \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update && apt-get install -y \
       python3.13 python3.13-venv python3.13-dev python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Work directory
WORKDIR /chopchop

# Copy only what’s needed
COPY . .

# Virtual environment setup
RUN python3.13 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Default command: interactive shell
CMD ["/bin/bash"]
