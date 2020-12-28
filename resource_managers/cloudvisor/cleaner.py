import asyncio
import logging
import aiohttp

from cloudvisor.cloud_vm import VM
from cloudvisor.ec2_wrapper import EC2Wrapper


class Cleaner(object):
    def __init__(self, manager, provisioner_ep):
        self.provisioner_ep = provisioner_ep
        self.ec2_manager = manager

    async def active_allocation_ids(self):
        uri = "http://%s/api/jobs" % self.provisioner_ep
        logging.info(f"getting allocations from {uri}")
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
        active_vms = await self.ec2_manager.list_active_vms()
        logging.info(f"cleaner: num active allocations: {len(active_allocations)}; active vms: {len(active_vms)}")
        for vm in active_vms:
            if vm.allocation_id not in active_allocations:
                logging.info(f"found dangling vm: {vm.allocation_id} \n{vm.json}\n")
                if vm.long_lasting:
                    logging.warning(f"long-lasting instance. reason: {vm.long_lasting()}.. skipping")
                    continue

                instance_creator = vm.tags['cloudvisor_id']
                # I want to avoid the situation where 1 cloudvisor creates a machine via 1 provisioner but the cleaner
                # of a different cloudvisor removes it because it obv doesnt appear in her redis allocations
                # So if they dont have the same parent and they arent both from main_cloudvisors I want to skip
                if instance_creator != self.ec2_manager.ec2_wrapper.id and \
                        EC2Wrapper.main_cloudvisor(self.ec2_manager.ec2_wrapper.id) != EC2Wrapper.main_cloudvisor(instance_creator):
                    logging.warning(f"vm wasnt created by {self.ec2_manager.ec2_wrapper.id}, "
                                    f"rather {vm.tags['cloudvisor_id']}. skipping")
                    continue

                # Must have the same creator, so lets destroy it.
                logging.warning(f"adding destroy_instance({vm.name}) to tasks")
                tasks.append(self.ec2_manager.destroy_instance(vm.name))
            else:
                logging.info("instance is an active allocation")

        if tasks:
            logging.info("awaiting gather of destory tasks...")
            await asyncio.gather(*tasks)
            logging.info("done cleaning dangling vms")
        else:
            logging.info("no dangling vms :)")

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
