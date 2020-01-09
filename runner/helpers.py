import logging
import socket
from paramiko.ssh_exception import NoValidConnectionsError, AuthenticationException, SSHException

from infra.plugins.ssh import SSHCalledProcessError


def hardware_config(hardware):
    def wrapper(func):
        func.__hardware_reqs = hardware
        return func
    return wrapper


def use_gravity_exec(connected_ssh_module):
    if is_k8s(connected_ssh_module):
        return 'sudo gravity exec'
    else:
        return ''


def is_k8s(connected_ssh_module):
    try:
        connected_ssh_module.execute("sudo kubectl get po")
        return True
    except SSHCalledProcessError:
        return False


def deploy_proxy_container(connected_ssh_module, auth_args=['password', 'root', 'pass']):
    removed = remove_proxy_container(connected_ssh_module)
    if removed:
        logging.warning("Unexpected behavior: removed proxy container despite that I shouldn't have needed to")

    logging.info("initializing docker")
    run_cmd = f'{use_gravity_exec(connected_ssh_module)} docker run -d --rm --network=host --name=ssh_container orihab/ubuntu_ssh:2.0 {" ".join(auth_args)}'
    connected_ssh_module.execute(run_cmd)
    logging.info("docker is running")


def remove_proxy_container(connected_ssh_module):
    try:
        logging.info("trying to remove docker container")
        connected_ssh_module.execute(f'{use_gravity_exec(connected_ssh_module)} docker rm -f ssh_container')
        logging.info("removed successfully!")
        return True
    except SSHCalledProcessError as e:
        if 'No such container' not in e.stderr:
            raise e
        logging.info("nothing to remove")


def connect_via_running_docker(base):
    try:
        base.host.SSH.docker_connect(base.host.SSH.TUNNEL_PORT)
        return
    except NoValidConnectionsError:
        logging.exception("no valid connections")
    except socket.timeout as e:
        logging.exception("socket timeout trying to connect via running docker")
    except AuthenticationException:
        logging.exception("Authentication failed")
    except SSHException:
        logging.exception("Error reading SSH protocol banner")
    except Exception as e:
        logging.exception(f"caught other exception: {e}")
    raise Exception("unsuccessful connecting via running docker...")


def init_docker_and_connect(host):
    logging.info(f"[{host}] connecting to ssh directly")
    host.SSH.connect()
    logging.info(f"[{host}] connected successfully")

    deploy_proxy_container(host.SSH)

    logging.info(f"[{host}] connecting to ssh container")
    host.SSH.docker_connect(host.SSH.TUNNEL_PORT)
    logging.info(f"[{host}] connected successfully")


def init_dockers_and_connect(hosts):
    for name, host in hosts:
        logging.info(f"[{name}: {host}] initializing machine ")
        init_docker_and_connect(host)
        logging.info(f"[{name}: {host}] success initializing docker and connecting to it")


def tear_down_docker(host):
    host.SSH.connect()
    remove_proxy_container(host.SSH)


def tear_down_dockers(hosts):
    for name, host in hosts:
        logging.info(f"[{name}: {host}] tearing down")
        tear_down_docker(host)
        logging.info(f"[{name}: {host}] success tearing down")

