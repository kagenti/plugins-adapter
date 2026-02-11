# Internal NemoCheck Plugin

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
1. Update `${project_root}/resources/config/config.yaml`. Sample file [here](/resources/config/nemocheck-internal-config.yaml)

    ```
    # plugins/config.yaml - Main plugin configuration file
    plugins:
      - name: "NemoCheckv2"
        kind: "plugins.examples.nemocheckinternal.plugin.NemoCheckv2"
        description: "Adapter for nemo check server"
        version: "0.1.0"
        config:
          checkserver_url: "http://nemo-guardrails-service:8000/v1/guardrail/checks"    
    # Plugin directories to scan
    plugin_dirs:
      - "plugins/examples/nemocheckinternal"    # Nemo Check Server plugins
    ```

1. In `config.yaml` ensure key `plugins.config.checkserver_url` points to the correct service
1. Start plugin adapter

# Test

1. Open mcp-inspector to the mcp-gateway
1. Try running a tool configured/not configured in nemo check config allow list in configmap [E.g.](/plugins/examples/nemocheck/k8deploy/config-tools.yaml)