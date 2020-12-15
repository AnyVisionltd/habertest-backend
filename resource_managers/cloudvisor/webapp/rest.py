import asyncio
import json
import logging
import uuid

from aiohttp import web

from cloudvisor.cloud_vm import VM
from cloudvisor.ec2_wrapper import EC2Wrapper


class CloudVisor(object):

    def __init__(self, webapp, ec2_manager):
        self.ec2_manager = ec2_manager
        webapp.router.add_routes([web.get('/', self.ping),
                                  web.get('/vms', self.handle_list_vms),
                                  web.get('/vms/{instance_id}', self.handle_vm_status),
                                  web.post('/vms', self.handle_allocate_vm),
                                  web.delete('/vms/{instance_id}', self.handle_destroy_vm),
                                  web.post('/fulfill/theoretically', self.check_fulfill),
                                  web.post('/fulfill/now', self.fulfill),
                                  web.delete('/deallocate/{instance_id}', self.handle_destroy_vm),
                                  web.get('/allocations/{allocation_id}', self.handle_get_allocation)])

    async def ping(self, request):
        return web.json_response({"status": "pong"}, status=200)

    async def handle_allocate_vm(self, request):
        data = await request.json()
        base_image = data.get('base_image')
        instance_type = data.get('instance_type')
        allocation_id = data.get("allocation_id", str(uuid.uuid4()))
        logging.info(f"allocationid: {allocation_id}")
        client_external_ip = data.get("client_external_ip")
        machine = VM(base_image=base_image, instance_type=instance_type,
                     client_external_ip=client_external_ip, allocation_id=allocation_id,
                     requestor=data.get('requestor', {}))
        machine = await self.ec2_manager.allocate_instance(machine)
        return web.json_response(
            {'status': 'Success', 'machine': machine.json}, status=200)

    async def handle_destroy_vm(self, request):
        instance_id = request.match_info['instance_id']
        logging.info(f"trying to delete instance: {instance_id}")
        await self.ec2_manager.destroy_instance(instance_id)
        return web.json_response(
            {'status': 'Success'}, status=200)

    async def handle_list_vms(self, _):
        instances = await self.ec2_manager.list_vms()
        return web.json_response(
            {'status': 'Success',
             'vms': [instance.json for instance in instances]},
            status=200)

    async def handle_vm_status(self, request):
        instance_id = request.match_info['instance_id']
        instance = next(iter(await self.ec2_manager.describe_vms(instance_id)))
        return web.json_response({'info': instance.json}, status=200)

    async def handle_get_allocation(self, request):
        allocation_id = request.match_info['allocation_id']
        instances = await self.ec2_manager.get_allocation(allocation_id)
        logging.info(f"result of get_allocation for {allocation_id}: {instances}")
        return web.json_response({'info': [instance.json] for instance in instances}, status=200)

    def translate_to_vms(self, request):
        vm_requests = list()
        client_external_ip = request['requestor']['external_ip']
        allocation_id = request.get('allocation_id', str(uuid.uuid4()))
        for host, reqs in request['demands'].items():
            base_image = reqs.pop("base_image", 'ami-0d53b078caae15158')
            instance_type = reqs.pop("instance_type", 'g4dn.2xlarge')
            instance = VM(client_external_ip=client_external_ip, base_image=base_image,
                          instance_type=instance_type, allocation_id=allocation_id,
                          requestor=request['requestor'])
            vm_requests.append(instance)
        return vm_requests

    async def check_fulfill(self, request):
        requirements = await request.json()
        logging.info(f"received a check_fulfill request: {requirements}")
        vm_requests = self.translate_to_vms(requirements)
        possible = list()
        for vm in vm_requests:
            possible.append(await self.ec2_manager.check_allocate_instance(vm))

        if all(possible):
            return web.json_response({"status": "Success"}, status=200)
        else:
            return web.json_response({"status": "Unable"}, status=406)

    async def fulfill(self, request):
        """request: demands: {{"host1": {"cpus": "value", "foo": "bar"},
        #                     "host2": {"cpus": "value", "foo": "bar"}},
        #                     "allocation_id":"1234-234523-2342-23424"}"""

        requirements = await request.json()
        logging.info(f"received a fulfill request: {requirements}")
        vm_requests = self.translate_to_vms(requirements)

        allocated_machines = await asyncio.gather(
            *[self.ec2_manager.allocate_instance(vm) for vm in vm_requests])
        return web.json_response(
                    {'status': 'Success', 'info': [vm.json for vm in allocated_machines]}, status=200)
