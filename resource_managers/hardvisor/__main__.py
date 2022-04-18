import argparse
import asyncio
import concurrent
import getpass
import logging
import os
import socket

import yaml
from aiohttp import web

import hardvisor
from hardvisor import manager, redis_client
from hardvisor import periodically
from utils import anylogging, ip, heartbeat


async def start_daemons(app):
    app["heartbeats"] = app.loop.create_task(
        heartbeat.send_heartbeats(app['info'], app['provisioner'], app['ssl_cert'], app['ssl_key']))

    app.loop.create_task(app["cleaner"].clean_dangling_hardware())


def load_machines_config(config_path, redis, loop):
    logging.info(f"config_path: {config_path}")
    with open(config_path) as f:
        machines = yaml.full_load(f)
    logging.info("running in executor")
    loop.run_until_complete(redis.update_machines(machines))
    logging.info("done running in executor")


if __name__ == '__main__':
    '''
    This can be run from resource_managers directory like: 
    python -m hardvisor args
    '''

    parser = argparse.ArgumentParser()
    parser.add_argument("--ip",
                        default=os.environ.get("HABERTEST_HARDVISOR_IP", ip.get_ip()),
                        help="ip address hardvisor is running which can receive fulfill requests"
                             "takes HABERTEST_HARDVISOR_IP env variable if exists")
    parser.add_argument("--port", default=os.getenv("HABERTEST_HARDVISOR_PORT", 9081))
    parser.add_argument("--config-path",
                        help="path to config file",
                        default=os.getenv("HABERTEST_HARDVISOR_CONFIG", os.path.expanduser("~/.habertest/hardvisor.yaml")))
    parser.add_argument("--log-level", default=os.getenv("LOG_LEVEL", "DEBUG"))
    parser.add_argument("--log-file-path", dest='log_file_path', default=os.getenv("LOG_FILE_PATH", '/var/log/hardvisor.log'))
    parser.add_argument("--hardvisor-id", default=os.getenv("HABERTEST_HARDVISOR_ID", f"{getpass.getuser()}-{socket.gethostname()}-hardvisor"))
    parser.add_argument("--provisioner", dest='provisioner', help="Provisioner address", type=str,
                        required=False, default=os.environ.get('HABERTEST_PROVISONER_ADDRESS'))
    parser.add_argument("--ssl-key", dest='ssl_key', help="Client certificate ssl private key", type=str,
                        required=False, default=os.environ.get('HABERTEST_SSL_KEY'))
    parser.add_argument("--ssl-cert", dest='ssl_cert', help="Client certificate ssl public key", type=str,
                        required=False, default=os.environ.get('HABERTEST_SSL_CERT'))

    args = parser.parse_args()
    anylogging.configure_logging(root_level=args.log_level, console_level=args.log_level, file_level=args.log_level,
                                 filename=args.log_file_path)

    app = web.Application()
    loop = asyncio.get_event_loop()
    redis_client = redis_client.RedisClient()

    load_machines_config(args.config_path, redis_client, loop)

    machine_manager = manager.HardwareManager(redis_client, loop)
    hardvisor.HardVisor(app, machine_manager)

    app["info"] = dict(alias=f'{args.hardvisor_id}', rm_type='hardvisor', endpoint=f'{args.ip}:{args.port}')

    if args.provisioner is not None:
        app["provisioner"] = args.provisioner
        if args.ssl_key:
            assert os.path.exists(args.ssl_key), f"cert file for communication with provisioner doesnt exist at {args.ssl_key}"
            app["ssl_key"] = args.ssl_key
        if args.ssl_cert:
            assert os.path.exists(args.ssl_cert), f"cert file for communication with provisioner doesnt exist at {args.ssl_cert}"
            app["ssl_cert"] = args.ssl_cert
        app["cleaner"] = periodically.Cleaner(args.provisioner, machine_manager, args.ssl_cert, args.ssl_key)
        logging.info(f"sending info: {app['info']} to provisioner {args.provisioner}")
        app.on_startup.append(start_daemons)

    web.run_app(app)
