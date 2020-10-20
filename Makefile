MODULES=hwallocator resource_managers

.PHONY: tests
tests: ## run all modules tests sequentially
	@FAILED=0; for dir in $(MODULES); do cd $(CURDIR)/$$dir && make tests || FAILED=1; done; \
	[ "$${FAILED}" = "0" ] || exit 1
