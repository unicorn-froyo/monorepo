FROM ubuntu:18.04

ENV PATH="$PATH:$HOME/bin"

RUN apt update && \
    apt upgrade -y

RUN apt-get update && \
    apt-get install software-properties-common -y

# c++ compiler dependencies
RUN apt install g++ unzip zip -y

# build container dependencies
RUN apt install curl -y

RUN apt-get install openjdk-11-jdk -y

RUN curl -s -L https://github.com/bazelbuild/bazel/releases/download/4.0.0/bazel-4.0.0-installer-linux-x86_64.sh \
    -o ./bazel-4.0.0-installer-linux-x86_64.sh && \
    chmod +x ./bazel-4.0.0-installer-linux-x86_64.sh && \
    ./bazel-4.0.0-installer-linux-x86_64.sh
