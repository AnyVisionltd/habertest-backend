MODULES=heartbeat_server provisioner

.PHONY: help
help: _help

.PHONY: run-provisioner
run-provisioner: ## runs the hwallocator (provisioner and hb server) in docker-compose
	@docker-compose up -d

.PHONY: tests
tests: ## run all modules tests sequentially
	@FAILED=0; for dir in $(MODULES); do cd $(CURDIR)/$$dir && make tests || FAILED=1; done; \
	[ "$${FAILED}" = "0" ] || exit 1

.PHONY: clean
clean: ## clean up environment
	@docker-compose rm

