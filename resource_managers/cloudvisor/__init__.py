import asyncio
import getpass
import os
import socket

import boto3

from cloudvisor.ec2_manager import EC2Manager
from cloudvisor.ec2_wrapper import EC2Wrapper


def init_managers():
    loop = asyncio.get_event_loop()
    ec2 = boto3.resource("ec2")
    vpc = EC2Wrapper.load_vpc(ec2, 'vpc-0e1b3b5e01c93e71e')
    info = EC2Wrapper.load_machine_key_info(ec2, 'anyvision-devops',
                                            f'{os.path.expanduser("~")}/.ssh/anyvision-devops.pem')

    wrapper = EC2Wrapper(vpc, info, ec2, f"{getpass.getuser()}-{socket.gethostname()}-cloudvisor")
    subnet_ids = ["subnet-0e210e70248adadac"]
    manager = EC2Manager(loop, wrapper, subnet_ids)
    return wrapper, manager