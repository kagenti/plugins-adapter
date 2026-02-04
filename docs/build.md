# Build Instructions

## Build Protocol Buffers

### Automated Build

```bash
python3 -m venv .venv
source .venv/bin/activate
./proto-build.sh
```

Verify `src/` contains: `/envoy`, `/validate`, `/xds`, `/udpa`

### Manual Build (Step by Step)

If you prefer not to use `proto-build.sh`:

1. **Install protoc and tools**

   See [instructions if needed](https://betterproto.github.io/python-betterproto2/getting-started/).

   ```sh
   pip install -r requirements-proto.txt
   ```

2. **Build Envoy protobufs**

   Code to help pull and build: `https://github.com/cetanu/envoy_data_plane.git`

   ```sh
   cd ..
   git clone git@github.com:cetanu/envoy_data_plane.git
   cd envoy_data_plane
   python build.py
   cd ..
   cp -r envoy_data_plane/src/envoy_data_plane_pb2/envoy plugins-adapter/src/
   ```

   NOTE: This builds envoy protos in `src/envoy_data_plane_pb2/`. Copy the `envoy` directory.

3. **Get XDS protobufs**

   ```sh
   git clone https://github.com/cncf/xds.git
   cp -rf xds/python/xds xds/python/validate xds/python/udpa plugins-adapter/src/
   ```

   NOTE: This repo contains python code for `validate`, `xds`, and `udpa`. Go to `python` folder.

4. **Install dependencies and run**

   ```sh
   pip install -r requirements.txt
   python src/server.py
   ```

You need `envoy`, `validate`, `xds`, `udpa` python protobuf folders in `src/` to run server.py
