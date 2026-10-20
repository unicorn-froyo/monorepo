#!/bin/sh
set -eu

build_dir=/tmp/get-widgets-rust
mkdir -p "$build_dir"
rustc --edition=2021 --crate-name api_base --crate-type=lib \
  src/apis/rust/abstract_api_base.rs --out-dir "$build_dir"
rustc --edition=2021 --crate-name get_widgets --crate-type=lib \
  get_widgets.rs \
  --extern api_base="$build_dir/libapi_base.rlib" --out-dir "$build_dir"
rustc --edition=2021 server.rs \
  -L dependency="$build_dir" \
  --extern get_widgets="$build_dir/libget_widgets.rlib" -o "$build_dir/server"
exec "$build_dir/server"
