# plugins-adapter

## Overview

An Envoy external processor (ext-proc) for configuring and invoking guardrails
in an Envoy-based gateway like [MCP Gateway](https://github.com/kagenti/mcp-gateway).
Intercepts gRPC traffic and applies configurable plugins (e.g., NeMo Guardrails).

## Repository Structure

```
plugins-adapter/
├── src/                  # Core server implementation (ext-proc gRPC server)
├── plugins/              # Plugin implementations
│   └── examples/         # Example plugins (nemocheck, etc.)
├── tests/                # Unit tests (pytest)
├── docs/                 # Architecture, build, deployment docs
├── resources/            # Kubernetes manifests and config
├── proto-build.sh        # Protobuf code generation script
├── ext-proc.yaml         # Envoy ExtProc deployment manifest
└── filter.yaml           # Envoy HTTP filter config
```

## Key Commands

| Task | Command |
|------|---------|
| Lint + Format | `make lint` |
| Test | `uv run pytest tests/ -v` |
| Build image | `make build PLUGIN_DEPS=nemocheck` |
| Deploy to Kind | `make all PLUGIN_DEPS=nemocheck` |
| Build protobufs | `uv sync --group proto && ./proto-build.sh` |
| Run locally | `make dev-run-nemocheck` |

## Code Style

- Python 3.11+ with `uv` package manager
- Linter/formatter: `ruff` (config in `pyproject.toml`)
- Pre-commit hooks: `pre-commit install`
- Sign-off required: `git commit -s`

## Plugin Development

Plugins live in `plugins/`. Each plugin implements the `cpex` interface.
See `plugins/examples/` for reference implementations.

Config in `resources/config/config.yaml`:
```yaml
plugins:
  - name: my_plugin
    path: ./plugins/my_plugin
    enabled: true
```

## DCO Sign-Off (Mandatory)

All commits must include a `Signed-off-by` trailer:

```sh
git commit -s -m "feat: add feature"
```
