#!/bin/sh
set -eu

# Resolve the executable from the installed gem instead of relying on generated
# command wrappers or the build worker's executable search path.
exec ruby -rbundler/setup -e 'load Gem.bin_path("puma", "puma")' -- \
  -b tcp://0.0.0.0:8080 src/apis/examples/ruby/config.ru
