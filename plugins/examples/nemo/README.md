# NeMo guardrails internal plugin example

The `NemoWrapperPlugin` in `nemo_wrapper_plugin.py` currently invokes the simple flow in `pii_detect_config` which leverages an ollama model through `host.docker.internal`. The model can be easily replaced in the `config.yml`.

How this works with the adapter:
- The `NemoWrapperPlugin` is referenced in the plugin manager config (`resources/config/config.yaml` by default).
- A plugins adapter image can be built with the nemoguardrails library using the `Dockerfile` in the repository.
- The plugins adapter image can then be replaced in the `ext-proc.yaml` deployment. The Envoy filter `filter.yaml` makes sure the Envoy gateway request will pass through the ext-proc.
- The MCP gateway can be brought up with `make inspect-gateway` or other methods. Test tool `test2_hello_world` can be used as a simple example to test PII/non-PII. As this is a simple example, there may be false positives.
