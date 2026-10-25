#!/usr/bin/env bash
set -euo pipefail

image=${1:-get-widgets-ruby:latest}
container=""
cleanup() {
  if [[ -n "$container" ]]; then
    docker logs "$container"
    docker rm -f "$container" >/dev/null
  fi
}
trap cleanup EXIT

# Check the installed payload before starting the service, so missing gems or
# ABI mismatches fail directly instead of looking like a readiness timeout.
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev \
  --entrypoint ruby "$image" -rbundler/setup -rpuma -rnio -rnokogiri -e '
    abort "unexpected Ruby" unless RUBY_VERSION == "4.0.7"
    abort "unexpected Bundler" unless Bundler::VERSION == "2.6.9"
    %w[puma nio4r nokogiri].each do |name|
      abort "gem outside packaged bundle: #{name}" unless Gem.loaded_specs.fetch(name).full_gem_path.start_with?("/usr/local/bundle/")
    end
    executable = Gem.bin_path("puma", "puma")
    abort "missing packaged Puma executable: #{executable}" unless File.file?(executable)
  '

# A read-only root and no network make startup installation impossible. Puma
# may use /tmp, but the installed bundle must stay unchanged in the image.
container=$(docker run -d --network none --read-only --tmpfs /tmp:rw,nosuid,nodev "$image")
for attempt in {1..60}; do
  if docker exec "$container" ruby -rnet/http -rjson -e '
    uri = URI("http://127.0.0.1:8080/widgets")
    response = Net::HTTP.get_response(uri)
    abort "wrong widgets response" unless response.code == "202" && JSON.parse(response.body) == []
    abort "missing security header" unless response["x-frame-options"] == "DENY"
    missing = Net::HTTP.get_response(URI("http://127.0.0.1:8080/missing"))
    abort "wrong missing-route response" unless missing.code == "404"
    abort "missing security header on 404" unless missing["x-content-type-options"] == "nosniff"
  '; then
    exit 0
  fi
  if [[ $(docker inspect --format '{{.State.Running}}' "$container") != true ]]; then
    exit 1
  fi
  sleep 1
done
echo "Ruby service did not become ready" >&2
exit 1
