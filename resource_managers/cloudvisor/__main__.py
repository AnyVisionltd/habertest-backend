import argparse
import asyncio
import getpass
import os
import socket

import boto3
from aiohttp import web

from cloudvisor.cleaner import Cleaner
from cloudvisor.ec2_manager import EC2Manager
from utils import anylogging, heartbeat, ip
from cloudvisor.webapp import rest

from cloudvisor.ec2_wrapper import EC2Wrapper
import logging


def _configure_logging(log_level):
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    anylogging.configure_logging(root_level=log_level, console_level=log_level, file_level=log_level,
                                 filename='/var/log/cloudvisor.log')


def resolve_ip():
    os.environ.get("HABERTEST_CLOUDVISOR_IP", ip.get_ip())


async def start_daemons(app):
    app["heartbeats"] = app.loop.create_task(
        heartbeat.send_heartbeats(app['info'], app['provisioner']))
    app.loop.create_task(app.cleaner.clean_periodically())
    
if __name__ == '__main__':
    DEFAULT_PEM_FILE_LOCATION = f'{os.path.expanduser("~")}/.ssh/anyvision-devops.pem'
    '''
    This can be run from resource_managers directory like: 
    python -m cloudvisor
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default=os.environ.get("HABERTEST_CLOUDVISOR_IP", ip.get_ip()), help="ip address cloudvisor is running which can receive fulfill requests"
                                                           "takes HABERTEST_CLOUDVISOR_IP env variable if exists")
    parser.add_argument("--port", default=os.getenv("SERVICE_PORT", 9080))
    parser.add_argument("--vpc", default=os.getenv("VPC_ID"))
    parser.add_argument("--key-name", default=os.getenv("KEY_PAIR_ID"))
    parser.add_argument("--pem-file", default=DEFAULT_PEM_FILE_LOCATION)
    parser.add_argument("--subnet-ids", type=str, nargs='+', default=os.getenv("SUBNET_IDS").split())
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "DEBUG"))
    parser.add_argument("--cloudvisor-id", default=os.getenv("HABERTEST_CLOUDVISOR_ID", f"{getpass.getuser()}-{socket.gethostname()}-cloudvisor"))
    parser.add_argument("--provisioner", dest='provisioner', help="Provisioner address", type=str,
                        required=False, default=os.environ.get('HABERTEST_PROVISONER_ADDRESS'))


    args = parser.parse_args()
    _configure_logging(args.log_level)

    ec2 = boto3.resource("ec2")
    vpc = EC2Wrapper.load_vpc(ec2, args.vpc)
    info = EC2Wrapper.load_machine_key_info(ec2, args.key_name, args.pem_file)

    loop = asyncio.get_event_loop()

    wrapper = EC2Wrapper(vpc, info, ec2, args.cloudvisor_id)
    manager = EC2Manager(loop, wrapper, args.subnet_ids)
    app = web.Application()

    rest.CloudVisor(app, manager)


    app["info"] = dict(alias=f'{getpass.getuser()}-{socket.gethostname()}-cloudvisor', rm_type='cloudvisor',
                       endpoint=f'{args.ip}:{args.port}')

    if args.provisioner is not None:
        app["provisioner"] = args.provisioner
        app.cleaner = Cleaner(provisioner_ep=app['provisioner'], manager=manager)
        logging.info(f"sending info: {app['info']} to provisioner {args.provisioner}")
        app.on_startup.append(start_daemons)

    web.run_app(app, port=args.port)

