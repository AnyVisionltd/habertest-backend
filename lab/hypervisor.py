from infra.utils import shell
from infra.utils import pci
from infra.utils import anylogging
import logging
from lab.vms import rest
from lab.vms import allocator
from lab.vms import vm_manager
from lab.vms import libvirt_wrapper
from lab.vms import image_store
import asyncio
from aiohttp import web
import argparse
import yaml


def _verify_gpu_drivers_not_loaded():
    nvidia_modules = shell.run_cmd("lsmod | grep nvidia")
    nouveau_modules = shell.run_cmd("lsmod | grep nouveau")
    if nvidia_modules or nouveau_modules:
        raise("Graphical kernel modules loaded nvidia: %s nouveau:\
        %s hypervisors cannot work with loaded modules", nvidia_modules, nouveau_modules)


def _check_kvm_ok():
    try:
        shell.run_cmd("kvm-ok")
    except:
        logging.error("KVM cannot run in accelerated mode are KVM modules exist?")
        raise


def load_config(file_name):
    config = {}
    with open(file_name, 'r') as f:
        config_yaml = yaml.load(f.read())
    if config_yaml.get('pcis', None) is not None:
        config['pci'] = [pci.Device.from_full_address(pci_conf['pci'])
                         for pci_conf in config_yaml['pcis']]
    else:
        config['pci'] = []
    config['macs'] = config_yaml['macs']
    return config


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Config file containing pci addresses and mac addressses", required=True)
    parser.add_argument("--qemu-uri", help="qemu uri", default="qemu:///system")
    parser.add_argument("--images-dir", help="Default backing images dir", default="var/lib/libvirt/images")
    parser.add_argument("--run-dir", help="Images run dir", default="var/lib/libvirt/images")
    parser.add_argument("--ssd-dir", help="SSD disks dir, where ssd images will be stored", default="var/lib/libvirt/images")
    parser.add_argument("--hdd-dir", help="HDD disks dir, where hdd images will be stored", default="var/lib/libvirt/images")
    parser.add_argument("--log-level", help="Log level defaults to INFO", default="INFO")
    parser.add_argument("--max-vms", help="Maximum amount of VMs to support concurrently", default=1, type=int)
    parser.add_argument("--private-net", help="Private network device for NAT networks", default="default")
    parser.add_argument("--paravirt-net-device", help="Paravirtualized network device for bridge networks", required=True)
    parser.add_argument("--sol-port", help="Base port for Serial over lan", required=True, type=int)
    parser.add_argument("--server-name", help="Name of the server, this will be used in name of VM`s", required=True)
    parser.add_argument("--port", help="HTTP port of hypervisor server", default=8080, type=int)

    args = parser.parse_args()
    log_level = logging.getLevelName(args.log_level)

    config = load_config(args.config)
    anylogging.configure_logging(root_level=log_level, console_level=log_level)
    loop = asyncio.get_event_loop()
    _check_kvm_ok()
    vmm = libvirt_wrapper.LibvirtWrapper(args.qemu_uri)
    storage = image_store.ImageStore(loop, base_qcow_path=args.images_dir,
                                     run_qcow_path=args.run_dir,ssd_path=args.ssd_dir, hdd_path=args.hdd_dir)
    gpu_pci_devices = config['pci']
    pci.vfio_bind_pci_devices(config['pci'])
    manager = vm_manager.VMManager(loop, vmm, storage)
    allocator = allocator.Allocator(mac_addresses=config['macs'], gpus_list=gpu_pci_devices, vm_manager=manager,
                                    server_name=args.server_name, max_vms=args.max_vms, private_network=args.private_net,
                                    paravirt_device=args.paravirt_net_device, sol_base_port=args.sol_port)
    app = web.Application()
    rest.HyperVisor(allocator, storage, app)
    web.run_app(app, port=args.port)