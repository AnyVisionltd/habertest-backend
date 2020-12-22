.PHONY: help
help: _help

.PHONY: run-provisioner
run-provisioner: build-provisioner ## runs the application
ifndef MYIP
	$(error MYIP is not set. Please set this to your machine IP)
endif
	@docker run --rm -e REDIS_USER=guest -e REDIS_PASSWORD=pAssw0Rd! -e REDIS_HOST=${MYIP} -e REDIS_PORT=6379 -e REDIS_DB=0 -v ${PWD}:/src -w /src -p 8080:8080 -ti allocate watchmedo auto-restart --recursive -d . -p '*.py' -- python3 -m 'webapp.app' serve

.PHONY: build-provisioner
build-provisioner:
	@docker build -t gcr.io/anyvision-training/habertest-provisioner .

.PHONY: push-provisioner
push-provisioner: build-provisioner
	@docker push gcr.io/anyvision-training/habertest-provisioner:latest

.PHONY: tests
tests:
	@cd ../.. && docker build -t unittests -f ./Dockerfile.unittests .
	@docker run --rm -w /root/habertest_backend/hwallocator/provisioner unittests bash -c "HABERTEST_PROVISIONER=192.168.70.7:8080 HABERTEST_HEARTBEAT_SERVER=192.168.70.7:7080 HABERTEST_RESOURCE_MANAGER=192.168.21.163:9080 python3 -m pytest tests -s"
