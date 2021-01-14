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
	@./deployment/hypervisor/run_hypervisor.sh

VPC_ID ?= vpc-0e1b3b5e01c93e71e
KEY_PAIR_ID ?= anyvision-devops
SUBNET_IDS ?= subnet-0e210e70248adadac

.PHONY: run-cloudvisor-host
run-cloudvisor-host:
	@watchmedo auto-restart --patterns="*.py" --recursive -- python -m cloudvisor --provisioner ${HABERTEST_PROVISIONER_ADDRESS}

.PHONY: build-cloudvisor
build-cloudvisor:
	@docker build -t gcr.io/anyvision-training/habertest-cloudvisor  -f Dockerfile.cloudvisor .

.PHONE: push-cloudvisor
push-cloudvisor: build-cloudvisor
	@docker push gcr.io/anyvision-training/habertest-cloudvisor:latest

.PHONY: run-cloudvisor-container
run-cloudvisor-container: build-cloudvisor
	@docker run --rm -v ${HOME}/.ssh:/root/.ssh -v ${HOME}/.aws:/root/.aws -v ${PWD}:/root/resource_managers -w /root/resource_managers -e HABERTEST_PROVISIONER_ADDRESS=${HABERTEST_PROVISIONER_ADDRESS} -e VPC_ID=${VPC_ID} -e KEY_PAIR_ID=${KEY_PAIR_ID} -e SUBNET_IDS=${SUBNET_IDS} --net host --name cloudvisor -it cloudvisor:latest bash

.PHONY: test-cloudvisor
test-cloudvisor: build-cloudvisor run-cloudvisor
	@docker run --rm -v ${HOME}/.ssh:/root/.ssh -v ${HOME}/.aws:/root/.aws -v ${PWD}:/root/resource_managers -w /root/resource_managers -e HABERTEST_PROVISIONER_ADDRESS=${HABERTEST_PROVISIONER_ADDRESS} -e VPC_ID=${VPC_ID} -e KEY_PAIR_ID=${KEY_PAIR_ID} -e SUBNET_IDS=${SUBNET_IDS} --net host --name cloudvisor_tests -it cloudvisor:latest python -m pytest tests/cloudvisor --log-cli-level info -s --pdb
	@docker stop cloudvisor

.PHONY: run-cloudvisor-daemon
run-cloudvisor-daemon: build-cloudvisor
	@docker stop cloudvisor || true
	@docker run --rm -d -v ${HOME}/.ssh:/root/.ssh -v ${HOME}/.aws:/root/.aws -v ${PWD}:/root/resource_managers -w /root/resource_managers -e HABERTEST_PROVISIONER_ADDRESS=${HABERTEST_PROVISIONER_ADDRESS} -e VPC_ID=${VPC_ID} -e KEY_PAIR_ID=${KEY_PAIR_ID} -e SUBNET_IDS=${SUBNET_IDS} --net host --name cloudvisor cloudvisor:latest python -m cloudvisor --provisioner ${HABERTEST_PROVISIONER_ADDRESS}

.PHONY: run-cloudvisor
run-cloudvisor: build-cloudvisor
	@docker stop cloudvisor || true
	@docker run --rm -v ${HOME}/.ssh:/root/.ssh -v ${HOME}/.aws:/root/.aws -v ${PWD}:/root/resource_managers -w /root/resource_managers -e HABERTEST_PROVISIONER_ADDRESS=${HABERTEST_PROVISIONER_ADDRESS} -e VPC_ID=${VPC_ID} -e KEY_PAIR_ID=${KEY_PAIR_ID} -e SUBNET_IDS=${SUBNET_IDS} --net host --name cloudvisor cloudvisor:latest python -m cloudvisor --provisioner ${HABERTEST_PROVISIONER_ADDRESS}


.PHONY: tests
tests: test-hypervisor test-cloudvisor

.PHONY: ipdb_ec2
ipdb_ec2:
	@PYTHONPATH=. python cloudvisor/ec2_wrapper_ipdb.py

.PHONY: config-hypervisor
config-hypervisor:
	@mv hypervisor/config/hypervisor.yaml hypervisor/config/hypervisor.yaml_bak || true
	@python3 hypervisor/tools/config_hypervisor.py -m $(vms)
	@cat hypervisor/config/hypervisor.yaml

.PHONY: hypervisor-logs
hypervisor-logs:
	@journalctl -f -t HYPERVISOR