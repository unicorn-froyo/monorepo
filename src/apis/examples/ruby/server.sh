#!/bin/sh
set -eu

bundle install --local
exec bundle exec puma -b tcp://0.0.0.0:8080 src/apis/examples/ruby/config.ru
