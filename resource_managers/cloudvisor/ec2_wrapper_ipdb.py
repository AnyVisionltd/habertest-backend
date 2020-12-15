import getpass
import os
import socket
import uuid
import asyncio
import boto3
import requests

from cloudvisor.cloud_vm import VM
from cloudvisor.ec2_manager import EC2Manager
from cloudvisor.ec2_wrapper import EC2Wrapper


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    ec2 = boto3.resource("ec2")
    vpc = EC2Wrapper.load_vpc(ec2, 'vpc-0e1b3b5e01c93e71e')
    info = EC2Wrapper.load_machine_key_info(ec2, 'anyvision-devops',
                                            f'{os.path.expanduser("~")}/.ssh/anyvision-devops.pem')

    wrapper = EC2Wrapper(vpc, info, ec2, f"{getpass.getuser()}-{socket.gethostname()}-cloudvisor")
    subnet_ids = ["subnet-0e210e70248adadac"]
    manager = EC2Manager(loop, wrapper, subnet_ids)
    machine = VM(base_image='ami-0e7c10ea30d385335',
                 client_external_ip=requests.get("http://ifconfig.me").text,
                 instance_type='g4dn.2xlarge',
                 allocation_id=str(uuid.uuid4()),
                 requestor=dict(hostname=socket.gethostname(), username=getpass.getuser(),
                                ip=socket.gethostbyname(socket.gethostname()),
                                external_ip=requests.get("http://checkip.amazonaws.com/").text.strip(),
                                long_lasting="GuyKlien asked for this"), )
    import pdb; pdb.set_trace()
