FROM ubuntu:24.04

ARG BAZELISK_VERSION=1.29.0

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
        ca-certificates \
        curl \
        g++ \
        libssl-dev \
        make \
        unzip \
        zip && \
    rm -rf /var/lib/apt/lists/*

RUN curl -fsSLo /usr/local/bin/bazelisk \
        "https://github.com/bazelbuild/bazelisk/releases/download/v${BAZELISK_VERSION}/bazelisk-linux-amd64" && \
    chmod +x /usr/local/bin/bazelisk && \
    ln -s /usr/local/bin/bazelisk /usr/local/bin/bazel
