#include .env

.PHONY: build load all
.IGNORE: redeploy-plugin


DOCKER_COMMAND := $(shell { command -v docker || command -v podman; } 2>/dev/null)


load:
	docker pull quay.io/rh-ee-mmisiura/nemo-guardrails:guardrails_checks_with_tools_o1_v1
	kind load docker-image quay.io/rh-ee-mmisiura/nemo-guardrails:guardrails_checks_with_tools_o1_v1 --name mcp-gateway


deploy:
	-kubectl delete -f server.yaml
	-kubectl delete -f config-tools.yaml
	kubectl apply -f config-tools.yaml
	kubectl apply -f server.yaml

all: pull-rits-webui load deploy
	@echo "pull build load deploy"

port-forward:
	kubectl port-forward -n istio-system service/nemo-guardrails-service 8000:8000

llmproxy-log:
	kubectl logs -f -n istio-system -l app=nemo-guardrails -c llm-proxy

guardrails-log:
	kubectl logs -f -n istio-system -l app=nemo-guardrails -c nemo-guardrails

logs: guardrails-log

pluginpod := $(shell kubectl get pod -n istio-system -l "app=nemo-guardrails"  -o name | sed 's/pod\///')
exec-plugin:
	kubectl exec -it -n istio-system ${pluginpod} -- bash
