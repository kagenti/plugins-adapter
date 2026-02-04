#!/bin/bash

pip install -r requirements-proto.txt
cd ..
git clone git@github.com:cetanu/envoy_data_plane.git
cd envoy_data_plane
python build.py
cd ..
rm -rf plugins-adapter/src/envoy || true
cp -r envoy_data_plane/src/envoy_data_plane_pb2/envoy plugins-adapter/src/

#envoy xds folders
git clone https://github.com/cncf/xds.git
rm -rf plugins-adapter/src/xds  plugins-adapter/src/validate plugins-adapter/src/udpa
cp -rf xds/python/xds xds/python/validate xds/python/udpa plugins-adapter/src/

cd plugins-adapter
