.PHONY: help
help: _help

.PHONY: run
run: build ## runs the application
ifndef MYIP
	$(error MYIP is not set. Please set this to your machine IP)
endif
	@docker run --rm -e REDIS_USER=guest -e REDIS_PASSWORD=pAssw0Rd! -e REDIS_HOST=${MYIP} -e REDIS_PORT=6379 -e REDIS_DB=0 -v ${PWD}:/src -w /src -p 8080:8080 -ti allocate watchmedo auto-restart --recursive -d . -p '*.py' -- python3 -m 'webapp.app' serve

.PHONY: build
build:
	@docker build -t=allocate .

.PHONY: tests
tests:
	HABERTEST_PROVISIONER=192.168.70.7:8080 HABERTEST_HEARTBEAT_SERVER=192.168.70.7:7080 HABERTEST_RESOURCE_MANAGER=192.168.70.35:9080 python -m pytest tests/test_provisioner.py -s --pdb

