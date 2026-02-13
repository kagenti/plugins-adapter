# NemoCheck Internal Plugin

This directory contains the core `NemoCheck` plugin implementation used by both internal and external plugins.

## Prerequisites: Nemo-check server
 * Refer to [orignal repo](https://github.com/m-misiura/demos/tree/main/nemo_openshift/guardrail-checks/deployment) for full instructions
 * Instructions adpated for mcpgateway kind cluster to work with an llm proxy routing to some open ai compatable backend below

   ```bash
	docker pull quay.io/rh-ee-mmisiura/nemo-guardrails:guardrails_checks_with_tools_o1_v1
	kind load docker-image quay.io/rh-ee-mmisiura/nemo-guardrails:guardrails_checks_with_tools_o1_v1 --name mcp-gateway
    cd plugins-adapter/plugins/examples/nemocheck/k8deploy
	kubectl apply -f config-tools.yaml
	kubectl apply -f server.yaml

   ```
## Installation

1. Find url of nemo-check-server service. E.g., from svc in `server.yaml`
1. Update `${project_root}/resources/config/config.yaml`. Add the blob below, merge if other `plugin`s or `plugin_dir`s already exists. Sample file [here](/resources/config/nemocheck-internal-config.yaml)

    ```yaml
    # plugins/config.yaml - Main plugin configuration file
    plugins:
      - name: "NemoCheck"
        kind: "plugins.examples.nemocheck.nemocheck.plugin.NemoCheck"
        description: "Adapter for nemo check server"
        version: "0.1.0"
        hooks: ["tool_pre_invoke", "tool_post_invoke"]
        mode: "enforce"  # enforce | permissive | disabled
        config:
          checkserver_url: "http://nemo-guardrails-service:8000/v1/guardrail/checks"
    # Plugin directories to scan
    plugin_dirs:
      - "plugins/examples/nemocheck"    # Nemo Check Server plugins
    ```

1. In `config.yaml` ensure key `plugins.config.checkserver_url` points to the correct service
1. Start plugin adapter

## Plugin Development

To install dependencies with dev packages (required for linting and testing):

```bash
make install-dev
```

Alternatively, you can also install it in editable mode:

```bash
make install-editable
```

## Setting up the development environment

1. Copy .env.template .env
2. Enable plugins in `.env`

## Testing

Test modules are created under the `tests` directory.

To run all tests, use the following command:

```bash
make test
```

**Note:** To enable logging, set `log_cli = true` in `tests/pytest.ini`.

## Code Linting

Before checking in any code for the project, please lint the code. This can be done using:

```bash
make lint-fix
```

# Test

1. Open mcp-inspector to the mcp-gateway
1. Try running a tool configured/not configured in nemo check config allow list in configmap [E.g.](/plugins/examples/nemocheck/k8deploy/config-tools.yaml)
