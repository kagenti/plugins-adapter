# NemoCheck External Plugin

This is an external plugin deployment for the NemoCheck guardrails adapter. It references the core `NemoCheck` implementation from the `nemocheck` plugin directory.

## Architecture

- **Core Implementation**: `plugins/examples/nemocheck/plugin.py` contains the actual NemoCheck logic
- **External Deployment**: This directory (`nemocheck_external`) configures and deploys the plugin as an external MCP server
- **Shared Logic**: Both internal and external deployments use the same underlying implementation to eliminate code duplication


## Run plugin in kind cluster

 1. Run Nemo Guardrails check server. Instructions [here](#Deploy-checkserver)
 1. Update `CHECK_ENDPOINT` variable in k8deploy/deploy.yaml to point to guardrails check server endpoint

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

## Test with MCP inspector
 * Add allowed tools to `plugins-adapter/plugins/examples/nemocheck/k8deploy/config-tools.yaml#check_tool_call_safety`
<table>
<tr>
<th> config-tools.yaml line-127</th>
<th>Updated to add test2_hello_world </th>
</tr>
<tr>
<td>
<pre>

```python
@action(is_system_action=True)
async def check_tool_call_safety(tool_calls=None, context=None):
    """Allow list for tool execution."""
      ...
      allowed_tools = ["get_weather", "search_web",
          "get_time", "slack_read_messages"]
      ...
```
</pre>
</td>
<td>

```python
@action(is_system_action=True)
async def check_tool_call_safety(tool_calls=None, context=None):
    """Allow list for tool execution."""
      ...
      allowed_tools = ["get_weather", "search_web", "get_time",
          "test2_hello_world", "slack_read_messages"]
      ...
```

</td>
</tr>
</table>


 * Redeploy check server
 * Open mcp inspector. Try tools in allow list vs tools not in allow list


## Deploy-checkserver
 * Refer to [orignal repo](https://github.com/m-misiura/demos/tree/main/nemo_openshift/guardrail-checks/deployment) for full instructions
 * Instructions adpated for mcpgateway kind cluster to work with an llm proxy routing to some open ai compatable backend below
 * Makefile has targets to load checkserver to kind cluster, etc.

   ```bash
   cd plugins-adapter/plugins/examples/nemocheck/k8deploy
   make deploy

   ```


## Testing

Tests are located in the `nemocheck` plugin directory since both deployments share the same core implementation.

See the [nemocheck README](../nemocheck/README.md#testing) for testing instructions.

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
