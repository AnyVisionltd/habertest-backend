.PHONY: run
run: build ## runs the application
ifndef MYIP
	$(error MYIP is not set. Please set this to your machine IP)
endif
	@docker run --rm -e REDIS_HOST=${MYIP} -e REDIS_PORT=6379 -e REDIS_DB=0 -e REDIS_USER=guest -e REDIS_PASSWORD=password -v ${PWD}:/src -w /src -p 7080:8080 -ti heartbeats watchmedo auto-restart --recursive -d . -p '*.py' -- python3 -m 'webapp.app' serve

.PHONY: build
build: ## builds the docker image
	@docker build -t=heartbeats .

.PHONY: tests
tests:
	@echo "TODO: write heartbeat_server unittests"
