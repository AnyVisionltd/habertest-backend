from pprint import pprint

import requests
import argparse

from hwallocator.provisioner.webapp.redisclient import RedisClient


def clean_dangling_vms(redis_client):
    redis_allocations = redis_client.allocations_sync()

    rm_eps = [rm['endpoint'] for rm in redis_client.resource_managers_sync()]
    print(rm_eps)

    for rm_ep in rm_eps:
        print(f"resource_manager {rm_ep}...")
        resp = requests.get(f"http://{rm_ep}/vms")
        vms = resp.json()['vms']
        for vm in vms:
            allocation_id = vm['allocation_id']
            if not allocation_id:
                print(f"found vm which was manually allocated: {(rm_ep, vm['name'])}")
                continue
            if allocation_id not in redis_allocations:
                print(f"found dangling vm: a_id: {allocation_id}, details: {(rm_ep, vm['name'])}")
                pprint(vm)
                delete = input("delete vm? (Y)\n")
                if delete.lower() == 'y':
                    res = requests.delete(f"http://{rm_ep}/vms/{vm['name']}")
                    assert res.status_code == 200, "Wasnt successful deleting vm :("
                    print("deleted.")
                else:
                    print("ok, not deleting vm.")

    print("done cleaning!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--redis-host", default='redis', help="ip address or hostname where habertest-backend redis is running")
    parser.add_argument("--redis-port", default=6379, help="port where habertest-backend redis is running")
    args = parser.parse_args()
    r = RedisClient(
        host=args.redis_host,
        port=args.redis_port,
        username="",
        password="",
        db=0,
    )
    clean_dangling_vms(r)
