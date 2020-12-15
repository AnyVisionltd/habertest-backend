.PHONY: test-hypervisor
test-hypervisor:
	@cd .. && docker build -t unittests -f ./Dockerfile.unittests .
	@docker run --rm -v $$PWD:/root/habertest_backend/resource_managers -w /root/habertest_backend/resource_managers unittests python3 -m pytest tests/hypervisor -vvv

.PHONY: build-hypervisor
build-hypervisor:
	docker build -f Dockerfile.hypervisor -t hypervisor:latest .
	@echo "Built hypervisor:latest"

.PHONY: run-hypervisor
run-hypervisor:
	@echo "TODO: cd hypervisor && ./deployment/hypervisor/run_hypervisor.sh"

.PHONY: tests
tests: test-hypervisor