import asyncio
import random
import uuid
from asyncio import shield

from . import rm_requestor
from .settings import log
from .redisclient import REDIS


class Fulfiller(object):
    def __init__(self):
        self.fulfill_lock = asyncio.Lock()
        self.redis = REDIS

    async def fulfill(self, allocation_request):
        """
        allocation_request = {"demands": {"host": {"whatever": "value", "foo": "bar"}},
                                "maybe_more_fields_like_priority_or_sender": "user|jenkins"}
        """
        allocation_id = allocation_request.get("allocation_id", str(uuid.uuid4()))
        allocation = await self.redis.allocations(allocation_id)
        if allocation:
            return allocation
        await self.redis.save_request(allocation_request)
        log.debug(f"trying to fulfill: {allocation_request}")

        potential_fulfillers = await self.find_potential_fulfillers(allocation_id)
        possible = True

        # Check if all resource_managers can togather provision requested machines
        if potential_fulfillers:
            possible_machines = set()
            for fulfiller in potential_fulfillers:
                possible_machines.update(fulfiller[1])
            if len(possible_machines) != len(allocation_request['demands'].keys()):
                possible = False
        else:
            possible = False

        if not possible:
            allocation = await self.redis.allocations(allocation_id)
            allocation.update(status="unfulfillable", message="Allocator doesnt have resource_managers which can fulfill demands")
            await self.redis.delete("allocations", allocation_id)
            return allocation

        log.debug(f"found potential fulfillers: {potential_fulfillers}")
        async with self.fulfill_lock:
            log.debug("holding fulfill_lock")

            # Remove from potential fullfiler hosts which other fulfillers can provision to avoid duplicates
            for potential_fulfiller, hosts in potential_fulfillers:
                tmp_fulfillers = potential_fulfillers.copy()
                tmp_fulfillers.remove((potential_fulfiller, hosts))
                for host in hosts:
                    if host in sum([tmp_hosts for fullfiler, tmp_hosts in tmp_fulfillers], []):
                        hosts.remove(host)

                await self.redis.update_status(allocation_id,
                                       status="allocating",
                                       rm_endpoint=potential_fulfiller['endpoint'],
                                       message="in progress")

            for fulfiller, hosts in potential_fulfillers:
                request = await self.redis.allocations(allocation_id)
                for host in list(request['demands']):
                    if host not in hosts:
                        request['demands'].pop(host)
                try:
                    result = await shield(
                        rm_requestor.allocate(fulfiller['endpoint'], request))
                except asyncio.CancelledError:
                    log.debug(f"allocate task was cancelled.")
                    await self.redis.update_status(allocation_id, status="cancelled",
                                                   message="client cancelled after allocation started but before allocation was finish")
                    break

                except Exception as e:
                    log.debug(f"exception {type(e)} when trying to allocate on rm {fulfiller}")
                    await self.redis.update_status(allocation_id, status="exception", message=str(e))

                    log.exception(f"{fulfiller['alias']} couldnt fulfill demands.")
                    break

                log.debug(f'suceeded fullfilling request: {result}')
                await self.redis.save_fulfilled_request(allocation_id, fulfiller, result)
            return await self.redis.allocations(allocation_id)

        log.debug("released fulfill_lock")
        await self.redis.update_status(allocation_id, status="busy",
                                 message="Currently unable to fulfill requirements but should be able to in the future")
        return await self.redis.allocations(allocation_id)

    async def choose_from(self, resource_managers):
        # TODO: placeholder to enable some type of logic
        return random.choice(resource_managers)

    async def remove_unavailable_rms(self, live_rms, all_rms):
        live = {potential[0]['key'] for potential in live_rms}
        rms = set(key for key in all_rms.keys())
        dead = list(rms.difference(live))
        if dead:
            log.debug(f"found dead resource_managers: {dead}")
            await self.redis.delete("resource_managers", dead)
            log.debug("deleted resource_managers")

    async def find_potential_fulfillers(self, allocation_id):
        allocation_request = await self.redis.allocations(allocation_id)
        resource_managers = await self.redis.resource_managers()
        tasks = list()
        for key, resource_manager in resource_managers.items():
            resource_manager['key'] = key
            tasks.append(rm_requestor.theoretically_fulfill(resource_manager, allocation_request))
        potentials = await asyncio.gather(*tasks, return_exceptions=True)
        potentials = [possible_rm for possible_rm in potentials if not isinstance(possible_rm, Exception)]

        await self.remove_unavailable_rms(potentials, resource_managers)

        log.debug(f"final potentials: {potentials}")
        return potentials

    async def release(self, allocation_id):
        allocation = await self.redis.allocations(allocation_id)
        if not allocation:
            return
        log.debug(f"received release request for allocation {allocation}")
        for hardware_details in allocation.get('hardware_details', []):
            await rm_requestor.deallocate(hardware_details['vm_id'], hardware_details['resource_manager_ep'])
        await self.redis.update_status(allocation_id, status="deallocated")
        await self.redis.delete('allocations', [allocation_id])
