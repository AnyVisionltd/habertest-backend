.PHONY: run-heartbeat
run-heartbeat: build-heartbeat ## runs the application
ifndef MYIP
	$(error MYIP is not set. Please set this to your machine IP)
endif
	@docker run --rm -e REDIS_HOST=${MYIP} -e REDIS_PORT=6379 -e REDIS_DB=0 -e REDIS_USER=guest -e REDIS_PASSWORD=password -v ${PWD}:/src -w /src -p 7080:8080 -ti heartbeats watchmedo auto-restart --recursive -d . -p '*.py' -- python3 -m 'webapp.app' serve

.PHONY: build-heartbeat
build-heartbeat: ## builds the docker image
	@docker build -t gcr.io/anyvision-training/habertest-heartbeat .

.PHONY: push-heartbeat
push-heartbeat: build-heartbeat
	@docker push gcr.io/anyvision-training/habertest-heartbeat:latest

.PHONY: tests
tests:
	@cd ../.. && docker build -t unittests -f ./Dockerfile.unittests .
	@docker run --rm -w /root/habertest_backend/hwallocator/heartbeat_server unittests bash -c "python3 -m pytest tests -s"
