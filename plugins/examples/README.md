# Plugin Examples

Example plugins demonstrating integration with the Plugins Adapter

## Available Examples

### nemo
Internal plugin that wraps NeMo Guardrails for PII detection using an Ollama model
- **Type**: Internal (same deployment)
- See [nemo/README.md](./nemo/README.md) for details

### nemocheck
External plugin adapter for NeMo Guardrails check server
- **Type**: External (separate service)
- Requires separate NeMo check server deployment
- See [nemocheck/README.md](./nemocheck/README.md) for details

## Usage

Reference plugins in the plugin adapter config (default at `resources/config/config.yaml`):

**Internal plugin:**
```yaml
plugins:
  - name: nemo
    kind: "plugins.examples.nemo.nemo_wrapper_plugin.NemoWrapperPlugin"
```

**External plugin:**
```yaml
plugins:
  - name: nemocheck
    kind: external
    mcp:
        proto: STREAMABLEHTTP
        url: http://nemocheck-plugin-service:8000/mcp
```
