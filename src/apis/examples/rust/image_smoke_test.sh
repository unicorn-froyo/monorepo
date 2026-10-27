#!/bin/bash
# The server must start and handle requests without any container networking.
set -euo pipefail

image=${1:-get-widgets-rust:latest}
expected_arch=${ARCH:?ARCH must name the expected Docker image architecture}

[[ "$(docker image inspect "$image" --format '{{.Architecture}}')" == "$expected_arch" ]]
[[ "$(docker image inspect "$image" --format '{{json .Config.Entrypoint}}')" == '["/app/server"]' ]]

container=$(docker run --detach --network none --read-only --cap-drop ALL "$image")
trap 'docker logs "$container"; docker rm --force "$container" >/dev/null' EXIT

request() {
  docker exec "$container" bash -c '
    exec 3<>/dev/tcp/127.0.0.1/8080
    printf "GET %s HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n" "$1" >&3
    cat <&3
  ' bash "$1"
}

response=
for attempt in {1..30}; do
  if response=$(request /widgets 2>/dev/null); then
    break
  fi
  sleep 1
done

check_response() {
  local response=$1 status=$2
  response=$(printf '%s' "$response" | tr -d '\r')
  [[ "$response" == "HTTP/1.1 $status "* ]]
  for header in \
    'x-content-type-options: nosniff' \
    'x-frame-options: DENY' \
    'referrer-policy: no-referrer' \
    'permissions-policy: camera=(), microphone=(), geolocation=()'; do
    printf '%s\n' "$response" | grep -Fxi -- "$header" >/dev/null
  done
  if printf '%s\n' "$response" | grep -qi '^strict-transport-security:'; then
    echo 'Unexpected HSTS on an HTTP connection' >&2
    exit 1
  fi
}

check_response "$response" 202
[[ "$response" == *$'\r\n\r\n[]' ]]
check_response "$(request /missing)" 404
echo 'Rust image has the expected architecture and entrypoint and serves /widgets and /missing with networking disabled and a read-only root filesystem.'
