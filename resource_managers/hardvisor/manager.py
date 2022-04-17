import asyncio
import logging

from hardvisor import remote_executor, cleaner


class HardwareManager:
    def __init__(self, redis, loop):
        self.loop = loop
        self.redis = redis
        self.allocate_lock = asyncio.Lock()

    async def machine_status(self, machine_name):
        return await self.redis.machines(machine_name)

    async def all_machines(self):
        return await self.redis.machines()

    async def fulfills_reqs(self, machine, reqs):
        # todo: for now, placeholder
        return True

    async def matching_machines(self, reqs):
        machines = await self.redis.machines()
        matching_machines = list()
        for machine in machines.values():
            if self.fulfills_reqs(machine, reqs):
                matching_machines.append(machine)
        return matching_machines

    async def match_reqs_to_available_machine(self, reqs):
        for machine in await self.matching_machines(reqs):
            if machine.get('status', 'available') == 'available':
                return machine
        return None

    async def check_allocate(self, requirements):
        return bool(await self.matching_machines(requirements))

    async def allocate(self, requirements):
        async with self.allocate_lock:
            machine = await self.match_reqs_to_available_machine(requirements)
            if machine:
                reserved_machine = await self.reserve_machine(machine, requirements)
                return reserved_machine
            return None

    @staticmethod
    async def clean(r_executor):
        await r_executor.reboot()
        await cleaner.clean(r_executor)
        await r_executor.reboot()

    async def reserve_machine(self, machine, reqs):
        machine['net_ifaces'] = list()
        machine['net_ifaces'].append({'ip': machine['ip']})
        machine['allocation_id'] = reqs.get('allocation_id', None)
        machine['requestor'] = reqs.get('requestor', None)
        machine['status'] = 'in_use'
        await self.redis.update_resource(machine['name'], machine)
        return machine

    async def release(self, machine_name):
        machine = await self.redis.machines(machine_name)
        if not machine:
            logging.error(f"received release request for {machine_name} but couldn't find machine...")
            return
        r_executor = remote_executor.RemoteExecutor(machine)
        # await self.clean(r_executor)
        if not machine.pop('allocation_id', None):
            logging.warning(f"received release request from machine {machine} that was not allocated")
        if machine.get('status', 'available') != 'in_use':
            logging.warning(f"received release request from machine {machine} that was not in use")
        machine['status'] = 'available'
        await self.redis.update_resource(machine_name, machine)

