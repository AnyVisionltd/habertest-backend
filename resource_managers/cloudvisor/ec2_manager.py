import asyncio
import concurrent
import itertools
import logging

from cloudvisor.cloud_vm import VM
from botocore.exceptions import ClientError

INSTANCE_TYPES_BY_GPU_COUNT = {'1': ['g3.4xlarge', 'g4dn.2xlarge', 'g4dn.4xlarge'],
                               '2': ['g3.8xlarge'],
                               '4': ['g4dn.12xlarge', 'g3.16xlarge'],
                               '8': ['p2.8xlarge', 'p3.16xlarge' ]}


class EC2Manager(object):
    def __init__(self, loop, ec2_api, subnet_ids):
        self.loop = loop
        self.ec2_wrapper = ec2_api
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=50)
        self.subnet_ids = itertools.cycle(subnet_ids)

    @classmethod
    async def convert_to_vms(cls, instances):
        vms = list()
        for instance in instances:
            assert not isinstance(instance, VM) and not isinstance(instance, dict), \
                f"Instance is of wrong type: {type(instance)}"
            vms.append(VM.from_aws_instance(instance))
        return vms

    async def allocate_instance(self, vm):
        subnet_id = next(self.subnet_ids)
        vm.net_ifaces = [{"subnet": subnet_id}]

        if vm.instance_type:
            instance_types = [vm.instance_type]
        else:
            try:
                instance_types = INSTANCE_TYPES_BY_GPU_COUNT[vm.num_gpus]
            except KeyError:
                raise KeyError(f"Instance type with {vm.num_gpus} is not defined.")

        for idx, type in enumerate(instance_types):
            try:
                vm.instance_type = type
                created_instance = await self.loop.run_in_executor(self.thread_pool,
                                                                   lambda: self.ec2_wrapper.allocate(vm))
                break
            except ClientError as err:
                if idx == len(instance_types) - 1:
                    raise err

        running_instance = await self.loop.run_in_executor(self.thread_pool,
                                                           lambda: self.ec2_wrapper.await_running(created_instance))

        vm.instance_id = running_instance.id
        running_instance.num_cpus = running_instance.cpu_options['CoreCount'] * running_instance.cpu_options[
            'ThreadsPerCore']
        vm.net_ifaces[0]['ip'] = running_instance.public_ip_address
        vm.name = running_instance.instance_id
        vm.user = 'ubuntu'
        vm.pem_key_string = self.ec2_wrapper.machine_key_info['pem']
        return vm

    async def destroy_instance(self, instance_id):
        await self.loop.run_in_executor(self.thread_pool,
                                        lambda: self.ec2_wrapper.destroy(instance_id))
        return

    async def destroy_many(self, instance_ids):
        await asyncio.gather(*[self.destroy(instance_id) for instance_id in instance_ids])
        return

    async def destroy_all(self):
        actives = await self.list_active_vms()
        await asyncio.gather(*[self.destroy(active.id) for active in actives])

    async def list_vms(self, **kwargs):
        instances = await self.loop.run_in_executor(self.thread_pool,
                                                    lambda: self.ec2_wrapper.list(**kwargs))
        return await self.convert_to_vms(instances)

    async def get_allocation(self, allocation_id):
        vms = await self.list_vms(Filters=self.ec2_wrapper.dict_to_filter({"tag:allocation_id": allocation_id}))
        return vms

    async def list_active_vms(self):
        instances = await self.loop.run_in_executor(self.thread_pool,
                                                    lambda: self.ec2_wrapper.list_active())
        return await self.convert_to_vms(instances)

    async def describe_vms(self, instance_ids):
        instances = await self.loop.run_in_executor(self.thread_pool,
                                                    lambda: self.ec2_wrapper.describe(instance_ids))
        return await self.convert_to_vms(instances)

    async def check_allocate_instance(self, instance):
        possible = await self.loop.run_in_executor(self.thread_pool,
                                                   lambda: self.ec2_wrapper.check_allocate(instance))
        return possible

    async def delete_dangling_security_groups_async(self):
        await self.loop.run_in_executor(self.thread_pool,
                                        lambda: self.ec2_wrapper.delete_dangling_security_groups())
