# NemoCheck Internal Plugin

This directory contains the core `NemoCheck` plugin implementation used by both internal and external plugins.

## Prerequisites: Nemo-check server
 * Refer to [original repo](https://github.com/m-misiura/demos/tree/main/nemo_openshift/guardrail-checks/deployment) for full instructions
 * Instructions are adapted for the `mcp-gateway` kind cluster to work with an LLM proxy routing to an OpenAI-compatible backend below:

```bash
docker pull quay.io/opendatahub/odh-trustyai-nemo-guardrails-server:latest
kind load docker-image quay.io/opendatahub/odh-trustyai-nemo-guardrails-server:latest --name mcp-gateway
cd plugins-adapter/plugins/examples/nemocheck/k8deploy
make deploy
```

## Installation

1. Find url of nemo-check-server service. E.g., from svc in `server.yaml`
1. Update `${project_root}/resources/config/config.yaml`. Add the blob below, merge if other `plugin`s or `plugin_dir`s already exists. Sample file [here](/resources/config/nemocheck-internal-config.yaml)

    ```yaml
    # plugins/config.yaml - Main plugin configuration file
    plugins:
      - name: "NemoCheck"
        kind: "plugins.examples.nemocheck.plugin.NemoCheck"
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

## Testing

Test modules are created under the `tests` directory.

To run all tests:

```bash
python -m pytest tests/ -v
```

**Note:** To enable logging, set `log_cli = true` in `tests/pytest.ini`.

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
 * Open the MCP inspector provided by the MCP gateway. Try tools in the allow-list vs. tools not in the allow-list.
