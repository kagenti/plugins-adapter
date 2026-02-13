# NemoCheck External Plugin

This is an external plugin deployment for the NemoCheck guardrails adapter. It references the core `NemoCheck` implementation from the `nemocheck` plugin directory.

## Architecture

- **Core Implementation**: `plugins/examples/nemocheck/plugin.py` contains the actual NemoCheck logic
- **External Deployment**: This directory (`nemocheck_external`) configures and deploys the plugin as an external MCP server

## Run plugin in kind cluster

 1. Run Nemo Guardrails check server. Instructions are the same as in the internal plugin [here](../nemocheck/README.md#prerequisites-nemo-check-server)
 1. Update `CHECK_ENDPOINT` variable in [k8deploy/deploy.yaml](./k8deploy/deploy.yaml) to point to guardrails check server endpoint

    ```bash
    cd plugins-adapter/plugins/examples/nemocheck
    make deploy
    ```
 1.
    <details>
    <summary>Non-kind k8 cluster instructions</summary>

    ```bash
        cd plugins-adapter/plugins/examples/nemocheck
        make container-build
        # push image to your container repo and update image name in k8deploy/deploy.yaml
        kubectl apply -f k8deploy/deploy.yaml

    ```
    </details>

 1. Update plugin adapter to call this as an external plugin

   ```bash
   cd ../../.. #project root directory plugins-adapter`
   cp resources/config/external_plugin_nemocheck.yaml resources/config/config.yaml
   make all
   ```


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

## Runtime (server)

This project uses [chuck-mcp-runtime](https://github.com/chrishayuk/chuk-mcp-runtime) to run external plugins as a standardized MCP server.

To build the container image:

```bash
make build
```

To run the container:

```bash
make start
```

To stop the container:

```bash
make stop
```
