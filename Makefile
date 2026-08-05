RELEASE_NAME=districts-docs
REGISTRY=registry.digitalocean.com/kubernetes-prod

docker-build:
	docker build -t $(REGISTRY)/$(RELEASE_NAME):latest .

docker-push:
	docker push $(REGISTRY)/$(RELEASE_NAME):latest

import:
	python3 scripts/gitbook-import.py
