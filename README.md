# Plugins Adapter

An Envoy external processor (ext-proc) for configuring and invoking guardrails in an Envoy-based gateway like [MCP Gateway](https://github.com/kagenti/mcp-gateway).

## Quick Install

### Prerequisites
- [kubectl](https://kubernetes.io/docs/reference/kubectl/) configured in CLI

### Deploy with Pre-built Image
```bash
git clone https://github.com/kagenti/plugins-adapter.git
cd plugins-adapter
make deploy_quay
```

## Full Dev Build

1. **Build Protocol Buffers**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ./proto-build.sh
   ```

2. **Verify** `src/` contains: `/envoy`, `/validate`, `/xds`, `/udpa`

3. **Deploy to kind cluster**
   ```bash
   make all
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
