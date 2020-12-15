#!/usr/bin/env python3
import argparse
import json
import sys
import os
sys.path.append(os.path.dirname(__file__))
from common import resource_manager_api as api


def _do_create(args):
    data = {"base_image": args.image,
            "base_image_size" : args.size,
            "ram" : args.ram,
            "num_cpus": args.cpus,
            "networks" : args.networks_all,
            "num_gpus" : args.gpus,
            "disks" : [] }

    if args.ssd:
        data["disks"].append({"size" : args.ssd, "type" : "ssd", "mount" : "/ssd", "fs" : "xfs"})
    if args.hdd:
        data["disks"].append({"size" : args.hdd, "type" : "hdd", "mount" : "/storage", "fs": "xfs"})

    return api.create(args.allocator, data=data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--allocator", help="Allocator host:port", required=True)
    commands = parser.add_subparsers(title="command", dest="command")
    commands.required = True

    create = commands.add_parser("create", help="Create VM")
    create.add_argument("--image", help="Name of base image from which to create VM", required=True)
    create.add_argument("--size", help="Size of boot disk in GB", required=False)
    create.add_argument("--ram", help="Ram in GBytes", type=int, required=True)
    create.add_argument("--ssd", help="SSD disk in Gbytes", type=int, required=False)
    create.add_argument("--hdd", help="HDD disk in Gbytes", type=int, required=False)
    create.add_argument("--cpus", help="Number of CPU`s to allocate", type=int, required=True)
    create.add_argument("--networks", dest="accumulate", action="store_const", const=sum, default=max, help="Specify networks")
    create.add_argument("networks_all", metavar="N", type=str, nargs="+", help="Networks", default=["bridge"])
    create.add_argument("--gpus", help="Number of GPU`s to allocate", required=False, type=int, default=0)

    create = commands.add_parser("delete", help="Delete VM")
    create.add_argument("--name", help="Name of the VM to delete", required=True)

    create = commands.add_parser("images", help="List images")
    create = commands.add_parser("list", help="List vms")

    create = commands.add_parser('poweroff', help="Poweroff VM")
    create.add_argument('--name', help="Name of the VM to poweoff", required=True)

    create = commands.add_parser('poweron', help="Poweron VM")
    create.add_argument('--name', help="Name of the VM to poweron", required=True)

    create = commands.add_parser('info', help="Get VM information")
    create.add_argument('--name', help="Name of the VM", required=True)

    create = commands.add_parser('resources', help="List free resources (GPU/Network)")

    commands = {"create" : _do_create,
                "delete" : lambda args: api.delete(args.allocator, args.name),
                "images" : lambda args: api.list_images(args.allocator),
                "list"   : lambda args: api.list_vms(args.allocator),
                "poweroff" : lambda args: api.update_vm(args.allocator, args.name, status={"power" : "off"}),
                "poweron" : lambda: api.update_vm(args.allocator, args.name, status={"power" : "on"}),
                "info" : lambda: api.vm_info(args.allocator, args.name),
                "resources" : lambda: api.resources(args.allocator)}

    args = parser.parse_args()
    result = commands[args.command](args)
    print(json.dumps(result.json()))
