# Use an ARM-based Python image
FROM --platform=linux/arm64 python:3.9-buster

# Install required system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    unzip \
    xz-utils \
    clang \
    cmake \
    ninja-build \
    pkg-config \
    libgtk-3-dev \
    liblzma-dev \
    libpcsclite1 \
    libpcsclite-dev \
    pcscd  # Smartcard daemon (needed for pyscard)

# Fix: Upgrade CMake to a version that supports ARCHIVE_EXTRACT
RUN apt-get remove -y cmake && \
    curl -fsSL -o cmake-linux.sh https://github.com/Kitware/CMake/releases/download/v3.22.6/cmake-3.22.6-linux-aarch64.sh && \
    chmod +x cmake-linux.sh && \
    ./cmake-linux.sh --prefix=/usr/local --skip-license && \
    rm cmake-linux.sh

# Verify CMake version
RUN cmake --version

# Create a new user
RUN useradd -ms /bin/bash fletuser

# Set the working directory inside the container
WORKDIR /app

# Copy project files
COPY . .

# Download and install Flutter 3.27.4
RUN git clone -b 3.27.4 https://github.com/flutter/flutter.git /flutter
ENV PATH="/flutter/bin:$PATH"

# Fix: Download all necessary Flutter dependencies (including Dart SDK)
RUN flutter doctor && flutter precache --linux
RUN flutter --version

# Create a virtual environment and install dependencies
RUN python3 -m venv /app/venv
RUN /app/venv/bin/pip install --no-cache-dir flet pyscard

# Change ownership to the new user
RUN chown -R fletuser:fletuser /app /flutter

# Switch to non-root user
USER fletuser

# Build the app using the virtual environment
RUN /app/venv/bin/flet build linux

# Set the default command
CMD ["./dist/main"]
