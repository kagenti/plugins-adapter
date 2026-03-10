#!/bin/bash
# Proto Build Script for envoy_data_plane
#
# This script builds protocol buffer files from the envoy_data_plane repository.
#
# Tested and working with:
#   envoy_data_plane commit: 86181df8ddb05f1d07994e58374fb93139d2bb70
#
# Dependencies:
#   - betterproto2==0.9.1
#   - betterproto2_compiler==0.9.0
#   - structlog, requests, grpcio-tools

set -euo pipefail

# Sync proto dependencies first in the current project
uv sync --group proto

cd ..
git clone git@github.com:cetanu/envoy_data_plane.git
cd envoy_data_plane || exit

# Checkout the specific commit that is known to work
ENVOY_DATA_PLANE_COMMIT="86181df8ddb05f1d07994e58374fb93139d2bb70"
git checkout "$ENVOY_DATA_PLANE_COMMIT"

# Install dependencies in the current uv environment (not a new one)
# These are needed by the envoy_data_plane build.py script
uv pip install --system structlog requests grpcio-tools betterproto2==0.9.1 betterproto2_compiler==0.9.0

# Run the build script directly (dependencies are now in the system/current environment)
python build.py

cd .. || exit

# The new structure outputs to src/envoy_data_plane_pb2 relative to envoy_data_plane directory
rm -rf plugins-adapter/src/envoy || true
cp -r envoy_data_plane/src/envoy_data_plane_pb2/envoy plugins-adapter/src/

# Copy xds, validate, and udpa from the BUILD directory created by build.py
# The new build.py creates these in the BUILD subdirectory
if [ -d "envoy_data_plane/BUILD/xds" ]; then
    rm -rf plugins-adapter/src/xds plugins-adapter/src/validate plugins-adapter/src/udpa
    cp -rf envoy_data_plane/BUILD/xds plugins-adapter/src/ 2>/dev/null || true
    cp -rf envoy_data_plane/BUILD/validate plugins-adapter/src/ 2>/dev/null || true
    cp -rf envoy_data_plane/BUILD/udpa plugins-adapter/src/ 2>/dev/null || true
else
    # Fallback to old xds clone method if BUILD directory doesn't have them
    git clone https://github.com/cncf/xds.git
    rm -rf plugins-adapter/src/xds plugins-adapter/src/validate plugins-adapter/src/udpa
    cp -rf xds/python/xds xds/python/validate xds/python/udpa plugins-adapter/src/
fi

cd plugins-adapter || exit
