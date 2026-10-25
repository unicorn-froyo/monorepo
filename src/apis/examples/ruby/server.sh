#!/bin/sh
set -eu

exec bundle exec puma -b tcp://0.0.0.0:8080 src/apis/examples/ruby/config.ru
