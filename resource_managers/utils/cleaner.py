import logging
import time
import aiohttp


async def clean_dangling_vms(hypervisor, provisioner_ep):
    logging.debug(f'cleaning dangling vms')
    while True:
        try:
            vms = hypervisor.vms
            async with aiohttp.ClientSession() as client:
                uri = f"http://{provisioner_ep}/api/jobs"
                async with client.get(uri) as resp:
                    j_resp = await resp.json()
                    if j_resp["status"] != 200:
                        logging.exception("get allocations failed.. Is allocator configure correctly?")
                    live_allocations = j_resp["data"]
                    allocation_ids = [allocation['allocation_id'] for allocation in live_allocations]
            for vm in vms:
                logging.debug(f"iterating over vms..")
                if vm.allocation_id not in allocation_ids:
                    logging.debug(f"found dangling vm: {vm.name}, {vm.allocation_id}")
                    await hypervisor.destroy_vm(vm.name)
                else:
                    logging.debug("vm active")
            time.sleep(60)
        except:
            continue
