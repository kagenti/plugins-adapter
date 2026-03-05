# NeMo guardrails internal plugin example

The `NemoWrapperPlugin` in `nemo_wrapper_plugin.py` currently invokes the simple flow in `pii_detect_config` which leverages an ollama model through `host.docker.internal`. The model can be easily replaced in the `config.yml`.

## Dependencies

This plugin requires the `nemoguardrails` library. The dependency is specified in `requirements.txt` in this directory.

### Docker Build

To build the Docker image with nemo plugin support:

```bash
# Build with nemo plugin dependencies included
docker build --build-arg PLUGIN_DEPS="nemo" -t plugins-adapter:with-nemo .

# Build with multiple plugin dependencies
docker build --build-arg PLUGIN_DEPS="nemo,other_plugin" -t plugins-adapter .

# Build without plugin dependencies (default)
docker build -t plugins-adapter .
```

### Local Development

For local development:
```bash
pip install -r plugins/examples/nemo/requirements.txt
```

## How this works with the adapter

- The `NemoWrapperPlugin` is referenced in the plugin manager config (`resources/config/config.yaml` by default).
- A plugins adapter image can be built with the nemoguardrails library using the `Dockerfile` in the repository. The Dockerfile automatically detects and installs plugin-specific requirements.
- The plugins adapter image can then be replaced in the `ext-proc.yaml` deployment. The Envoy filter `filter.yaml` makes sure the Envoy gateway request will pass through the ext-proc.
- The MCP gateway can be brought up with `make inspect-gateway` or other methods. Test tool `test2_hello_world` can be used as a simple example to test PII/non-PII. As this is a simple example, there may be false positives.
