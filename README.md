An Envoy ext-proc to configure and invoke guardrails for MCP Gateway.

## Quick Install

* Expects configured kubectl in cli
* Use pre-built image to deploy 
    ```
    git clone https://github.com/kagenti/plugins-adapter.git
    cd plugins-adapter
    make deploy_quay
    ```

## Configure Plugins

* Update `resources/config/config.yaml` with list of plugins

## Full Dev Build

### Build proto

1. Install protoc. See instructions if [needed](https://betterproto.github.io/python-betterproto2/getting-started/)
- Install the proto compiler and tools: 
```
pip install grpcio-tools
pip install betterproto2_compiler
```
2. Build the python `envoy` protobufs
- Code to help pull and build the python code from proto files: https://github.com/cetanu/envoy\_data\_plane.git
- Run: python utils/download\_protobufs.py
NOTE: This will build the envoy proto in src/envoy\_data\_plane\_pb2. Copy the src/envoy\_data\_plane\_pb2/envoy to where you need it. 
3. Get the python xds protobufs:
```
git clone https://github.com/cncf/xds.git
```
NOTE: This repo contains the python code for `validate, xds, udpa`. Go to folder python. Copy the needed folders or run
setup.py to install.
4. In the end you need `envoy, validate, xds, udpa` python protobufs folders copied into `src` to run example server.py
5. Run `python server.py`


### Enable debug logs for mcp-gateway envoy routes if needed
* From mcp-gateway folder: 
`make debug-envoy-impl`

