# Plugins Adapter

An Envoy external processor (ext-proc) for configuring and invoking guardrails in an Envoy-based gateway like [MCP Gateway](https://github.com/kagenti/mcp-gateway).

## Quick Install

### Prerequisites
- [kubectl](https://kubernetes.io/docs/reference/kubectl/) configured in CLI

## Full Dev Build

1. **Install uv** (if not already installed): https://docs.astral.sh/uv/getting-started/installation/

2. **Install dependencies and build Protocol Buffers**
   ```bash
   uv sync --group proto
   ./proto-build.sh
   ```

3. **Verify** `src/` contains: `/envoy`, `/validate`, `/xds`, `/udpa`

4. **Deploy to kind cluster**
   ```bash
   # Replace plugin adapter, with nemocheck plugin loaded. Use a comma-separated list to include other plugins
   make all PLUGIN_DEPS=nemocheck
   ```

See [detailed build instructions](./docs/build.md) for manual build steps.

## Configure Plugins

Update `resources/config/config.yaml` with list of plugins:

```yaml
plugins:
  - name: my_plugin
    path: ./plugins/my_plugin
    enabled: true
```

**Note:** See [plugins/examples](./plugins/examples/) for example plugins.

Then deploy:
```bash
make all
```

## Detailed Documentation

- [Build Instructions](./docs/build.md) - Detailed protobuf build steps
- [Deployment Guide](./docs/deployment.md) - Deployment and debugging
- [Architecture](./docs/architecture/) - System design and diagrams
