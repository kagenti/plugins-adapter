#!/bin/bash
# Proto Build Script for envoy_data_plane
#
# This script builds protocol buffer files from the envoy_data_plane repository.
#
# Tested and working with:
#   envoy_data_plane commit: 86181df8ddb05f1d07994e58374fb93139d2bb70
#
# Dependencies are managed in pyproject.toml [dependency-groups.proto]:

set -euo pipefail

# Sync proto dependencies from pyproject.toml
# This installs all dependencies needed by envoy_data_plane build.py
uv sync --group proto

cd ..
git clone git@github.com:cetanu/envoy_data_plane.git
cd envoy_data_plane || exit

# Checkout the specific commit that is known to work
ENVOY_DATA_PLANE_COMMIT="86181df8ddb05f1d07994e58374fb93139d2bb70"
git checkout "$ENVOY_DATA_PLANE_COMMIT"

# Run the build script (dependencies already installed via uv sync)
python build.py

cd .. || exit

# Copy the compiled envoy protobuf files
rm -rf plugins-adapter/src/envoy || true
cp -r envoy_data_plane/src/envoy_data_plane_pb2/envoy plugins-adapter/src/

# The envoy_data_plane build.py only generates envoy protobufs in _pb2 format
# For xds, validate, and udpa, we need to get them from the xds repository
# which provides pre-compiled Python files
git clone https://github.com/cncf/xds.git
rm -rf plugins-adapter/src/xds plugins-adapter/src/validate plugins-adapter/src/udpa
cp -rf xds/python/xds xds/python/validate xds/python/udpa plugins-adapter/src/

cd plugins-adapter || exit
