include .env

.PHONY: build load all
.IGNORE: redeploy-plugin


DOCKER_COMMAND := $(shell { command -v docker || command -v podman; } 2>/dev/null)


pull-rits-webui:
	git clone git@github.ibm.com:Julian-Stephen/rits-webui.git; \
	cd rits-webui; \
	git submodule update --init --recursive; \
	cd lite-rits; \
	${DOCKER_COMMAND} build -f Dockerfile --build-arg RITS_API_KEY=${RITS_API_KEY} --tag llm-proxy:0.1.0 --tag localhost/llm-proxy:0.1.0 . 

pull-lite-rits:
	git clone git@github.ibm.com:Blueberry/lite-rits.git; \
	cd lite-rits; \
	${DOCKER_COMMAND} build -f Dockerfile --build-arg RITS_API_KEY=${RITS_API_KEY} --tag llm-proxy:0.1.0 --tag localhost/llm-proxy:0.1.0 . 
	
        	
load:
	kind load docker-image localhost/llm-proxy:0.1.0 --name mcp-gateway
	kind load docker-image quay.io/rh-ee-mmisiura/nemo-guardrails:guardrails_checks_with_tools_o1_v1 --name mcp-gateway


deploy:
	-kubectl delete -f server.yaml
	-kubectl delete secret -n istio-system rits-api-key
	kubectl create secret -n istio-system generic rits-api-key --from-env-file=.env
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
