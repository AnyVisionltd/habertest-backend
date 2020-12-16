import asyncio
import getpass
import socket
import uuid
import pytest
import requests

import cloudvisor
from cloudvisor.cloud_vm import VM


@pytest.mark.asyncio
async def test_basic_flow():
    wrapper, manager = cloudvisor.init_managers()
    instances = await manager.list_vms()
    actives = await manager.list_active_vms()
    machine = VM(base_image='ami-0e7c10ea30d385335',
                          client_external_ip=requests.get("http://checkip.amazonaws.com/").text.strip(),
                          instance_type='g4dn.2xlarge',
                          allocation_id=str(uuid.uuid4()),
                          requestor=dict(hostname=socket.gethostname(), username=getpass.getuser(),
                                            ip=socket.gethostbyname(socket.gethostname()),
                                            external_ip=requests.get("http://checkip.amazonaws.com/").text.strip()))
    instance = await manager.allocate_instance(machine)
    actives = await manager.list_active_vms()
    description = next(iter(await manager.describe_vms(instance.instance_id)))
    assert description.name == machine.instance_id
    description = next(iter(await manager.describe_vms(instance.instance_id)))
    assert description.state in ['pending', 'running']
    await manager.destroy_instance(machine.instance_id)
    description = next(iter(await manager.describe_vms(instance.instance_id)))
    assert description.state in ['shutting-down', 'terminated']

