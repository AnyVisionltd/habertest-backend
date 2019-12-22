# -*- coding: utf-8 -*-
import json

import pytest
from munch import DefaultFactoryMunch

from infra.model.base_config import BaseConfig
from infra.model.host import Host
from runner import hardware_initializer, helpers


@pytest.hookimpl()
def pytest_runtest_setup(item):
    # TODO: I cant run 2 tests with 1 hardware without reinitializing it.
    assert hasattr(item.function, '__hardware_reqs'), "need to set hardware requirements for test"
    hardware_config = hardware_initializer.init_hardware(item.function.__hardware_reqs)
    item.function.__initialized_hardware = json.loads(hardware_config)


@pytest.fixture()
def base_config(request):
    print("initing base config..")
    base = BaseConfig.fromDict(request.function.__initialized_hardware, DefaultFactoryMunch)
    base.host = Host(base.host)
    # TODO: switch if working in docker/k8s
    try:
        helpers.connect_via_running_docker(base)
        yield base
    except Exception:
        helpers.init_docker_and_connect(base)
        yield base
        helpers.tear_down_docker(base)