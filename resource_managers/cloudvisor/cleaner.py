import asyncio
import logging
import aiohttp

from cloudvisor.ec2_wrapper import EC2Wrapper


class Cleaner(object):
    def __init__(self, manager, provisioner_ep):
        self.provisioner_ep = provisioner_ep
        self.ec2_manager = manager

    async def active_allocation_ids(self):
        uri = "http://%s/api/jobs" % self.provisioner_ep
        logging.info(f"cleaner: getting allocations from {uri}")
        async with aiohttp.ClientSession() as client:
            async with client.get(
                    uri) as resp:
                data = await resp.json()
                if data['status'] != 200:
                    raise Exception(f"couldnt get jobs from ep: {uri}")
                active_allocation_ids = set(allocation['allocation_id'] for allocation in data['data'])
                return active_allocation_ids

    async def clean_dangling_vms(self):
        tasks = list()
        active_allocations = await self.active_allocation_ids()
        vms = await self.ec2_manager.list_active_instances()
        logging.info(f"cleaner: num active allocations: {len(active_allocations)}; active vms: {len(vms)}")
        for vm in vms:
            if vm.allocation_id not in active_allocations:
                logging.info(f"found dangling vm: {vm.allocation_id} \n{vm.json}\n")
                if vm.tags.get("requestor:long_lasting", False):
                    logging.warning(f"long-lasting instance. reason: {vm.tags['requestor:long_lasting']}.. skipping")
                    continue

                if vm.tags['cloudvisor_id'] != self.ec2_manager.ec2_wrapper.id:
                    if not (EC2Wrapper.main_cloudvisor_id(self.ec2_manager.ec2_wrapper.id) and EC2Wrapper.main_cloudvisor_id(vm.tags['cloudvisor_id'])):
                        logging.warning(f"vm wasnt created by {self.ec2_manager.ec2_wrapper.id}, "
                                    f"rather {vm.tags['cloudvisor_id']}. skipping")
                        continue

                logging.warning("destroying...")
                tasks.append(self.ec2_manager.destroy_instance(vm.name))
        await asyncio.gather(*tasks)

    async def clean_dangling_security_groups(self):
        logging.info("cleaning dangling security groups")
        await self.ec2_manager.delete_dangling_security_groups_async()
        logging.info("done cleaning security groups")

    async def clean_periodically(self):
        while True:
            try:
                await asyncio.gather(self.clean_dangling_vms(), self.clean_dangling_security_groups())
            except Exception as e:
                logging.exception("Caught exception in clean periodically: ")
            await asyncio.sleep(60*15)
