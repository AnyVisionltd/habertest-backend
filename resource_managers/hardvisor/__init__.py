import asyncio
import logging

from aiohttp import web


class HardVisor(object):

    def __init__(self, app, machine_manager):
        self.machine_manager = machine_manager
        app.add_routes([web.get('/', self.ping),
                        web.get('/machines', self.handle_list_machines),
                        web.get('/machines/{machine_name}', self.handle_machine_status),
                        web.post('/fulfill/theoretically', self.check_fulfill),
                        web.post('/fulfill/now', self.fulfill),
                        web.delete('/deallocate/{machine_name}', self.handle_release_machine),
                        web.get('/allocations/{allocation_id}', self.handle_get_allocation),
                        ])

    async def ping(self, request):
        return web.json_response({"status": "pong"}, status=200)

    @staticmethod
    def parse_requirements(request):
        allocation_id = request.get('allocation_id', None)
        requestor = request['requestor']
        machine_reqs = list()
        for host, reqs in request['demands'].items():
            machine = {"allocation_id": allocation_id,
                       "requestor": requestor,
                       "host": host}
            if "gpu" in reqs:
                machine['gpu'] = reqs.pop('gpu')
            if "cpu" in reqs:
                machine['cpu'] = reqs.pop("cpu")
            if "type" in reqs:
                machine['type'] = reqs.pop("type")

            machine['arch'] = reqs.pop("arch", 'x86_64')
            machine_reqs.append(machine)
        return machine_reqs

    async def handle_list_machines(self, request):
        machines = await self.machine_manager.all_machines()
        return web.json_response({'status': 'Success',
             'machines': [machine for machine in machines.values()]}, status=200)

    async def check_fulfill(self, request):
        requirements = await request.json()
        demands = self.parse_requirements(requirements)
        possibles = await asyncio.gather(*[
            self.machine_manager.check_allocate(demand) for demand in demands
        ])

        final_possibles = dict()
        for possible in possibles:
            final_possibles.update(possible)

        possibles = final_possibles


        if any(possibles.values()):
            return web.json_response({"status": "Success", "machines": [host for host, possible in possibles.items() if possible]}, status=200)
        else:
            return web.json_response({"status": "Unable"}, status=406)

    async def fulfill(self, request):
        requirements = await request.json()
        machine_demands = self.parse_requirements(requirements)
        allocated_machines = await asyncio.gather(*[
                self.machine_manager.allocate(demand) for demand in machine_demands
            ])
        if not all(allocated_machines):
            await asyncio.gather(*[
                self.machine_manager.release(machine['name']) for machine in allocated_machines if machine is not None
            ])
            return web.json_response({'status': 'Failed', 'error': 'matching resources busy, try again later'}, status=503)
        else:
            return web.json_response(
                {'status': 'Success', 'info': allocated_machines}, status=200)

    async def handle_release_machine(self, request):
        machine_name = request.match_info['machine_name']
        logging.info(f"trying to delete instance: {machine_name}")
        await self.machine_manager.release(machine_name)
        return web.json_response(
            {'status': 'Success'}, status=200)

    async def handle_get_allocation(self, request):
        result = list()
        allocation_id = request.match_info['allocation_id']
        all_machines = await self.machine_manager.all_machines()
        for machine in all_machines.values():
            if machine.get('allocation_id', None) == allocation_id:
                result.append(machine)
        return web.json_response(
                    {'info': result}, status=200)

    async def handle_machine_status(self, request):
        machine_name = request.match_info['machine_name']
        machine_info = await self.machine_manager.machine_status(machine_name)
        return web.json_response({'info': machine_info}, status=200)
