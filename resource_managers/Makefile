.PHONY: test-hypervisor
test-hypervisor:
	@docker build -t unittests -f Dockerfile.unittests .
	@docker run --rm -w /root/resource_managers unittests python3 -m pytest . -vvv

.PHONY: build-hypervisor
build-hypervisor:
	docker build -f Dockerfile.hypervisor -t hypervisor:latest .
	@echo "Built hypervisor:latest"

.PHONY: run-hypervisor
run-hypervisor:
	@echo "TODO: cd hypervisor && ./deployment/hypervisor/run_hypervisor.sh"
