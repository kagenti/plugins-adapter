.PHONY: build load all deploy exec log
.IGNORE: delete


SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

CONTAINER_RUNTIME ?= $(shell command -v docker >/dev/null 2>&1 && echo docker || echo podman)


# Base image name (without any prefix)
IMAGE_BASE ?= plugins-adapter
#IMAGE_TAG ?= latest
IMAGE_TAG ?= 0.1.0

# Handle runtime-specific image naming
ifeq ($(CONTAINER_RUNTIME),podman)
  # Podman adds localhost/ prefix for local builds
  IMAGE_LOCAL := localhost/$(IMAGE_BASE):$(IMAGE_TAG)
  IMAGE_LOCAL_DEV := localhost/$(IMAGE_BASE)-dev:$(IMAGE_TAG)
  IMAGE_PUSH := $(IMAGE_BASE):$(IMAGE_TAG)
else
  # Docker doesn't add prefix
  IMAGE_LOCAL := $(IMAGE_BASE):$(IMAGE_TAG)
  IMAGE_LOCAL_DEV := $(IMAGE_BASE)-dev:$(IMAGE_TAG)
  IMAGE_PUSH := $(IMAGE_BASE):$(IMAGE_TAG)
endif

# Build the combined broker and router 
build:
	$(CONTAINER_RUNTIME) build -t $(IMAGE_LOCAL) .

load:
	kind load docker-image $(IMAGE_LOCAL) --name mcp-gateway

podname := $(shell kubectl get pods -A |grep my-extproc | grep -v Terminating | awk '{print $$2}')
log:
	kubectl logs ${podname} -n istio-system -f

exec:
	kubectl exec -ti ${podname} -n istio-system -- bash

delete: IMAGE=$(IMAGE_PUSH)
delete:
	envsubst < ext-proc.yaml | kubectl delete -f -

deploy: IMAGE=$(IMAGE_PUSH)
deploy:
	envsubst < ext-proc.yaml | kubectl apply -f -
	kubectl apply -f filter.yaml


redeploy: delete deploy

push_image_quay: build
	$(CONTAINER_RUNTIME) tag $(IMAGE_LOCAL)  quay.io/julian_stephen/$(IMAGE_PUSH) 
	$(CONTAINER_RUNTIME) push quay.io/julian_stephen/$(IMAGE_PUSH) 

all: build load redeploy
	@echo "All done!"

deploy_quay: IMAGE=quay.io/julian_stephen/$(IMAGE_PUSH)
deploy_quay: 
	$(CONTAINER_RUNTIME) pull $(IMAGE)
	$(CONTAINER_RUNTIME) tag $(IMAGE) $(IMAGE_LOCAL)
	kind load docker-image $(IMAGE) --name mcp-gateway
	envsubst < ext-proc.yaml | kubectl apply -f -

