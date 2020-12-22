"""
allocate - expire (handles jobs expiring in redis)
"""
import asyncio
import json
import time

import aiohttp

from . import rm_requestor
from .settings import log


async def try_deallocate(ep, name):
    try:
        await rm_requestor.deallocate(name, ep)
    except:
        log.error(f"failed deallocating {name} on ep {ep}")
        raise


async def deallocate(allocation):
    for hardware in allocation['hardware_details']:
        rm_ep = hardware['resource_manager_ep']
        vm_name = hardware["vm_id"]
        await try_deallocate(rm_ep, vm_name)


async def expire_allocations(redis):
    """
    looks for expired jobs in redis and processes them
    """
    conn = await redis.asyncconn
    while True:
        try:
            log.debug("processing expired jobs")
            deallocate_tasks = dict()
            allocations = await redis.allocations()
            for allocation_id, allocation in allocations.items():
                if allocation['status'] not in ['received', 'allocating', 'success']:
                    log.debug(f"found {allocation_id} with status {allocation['status']}")
                    if not allocation.get("rm_endpoint", None):
                        log.debug("allocation doesnt have rm_endpoint.. removing")
                        await redis.delete("allocations", allocation_id)
                        continue
                    if allocation["expiration"] < time.time() - 15 * 60:
                        await redis.delete("allocations", allocation_id)
                        continue
                    try:
                        result = await rm_requestor.check_status(allocation['allocation_id'], allocation['rm_endpoint'])
                    except aiohttp.client_exceptions.ClientConnectorError as e:
                        log.debug("couldnt connect to rm_endpoint to get status of machine, updating status to unknown")
                        await redis.update_status(allocation_id, status="unknown",
                                                  message="Currently unable to check status")
                        continue
                    except:
                        log.exception(f"exception checking status of allocation_id {allocation}.. updating status to unknown")
                        await redis.update_status(allocation_id, status="unknown",
                                                  message="Currently unable to check status")
                        continue
                    log.debug(f"updated status: {result}")
                    if result['info']:
                        await redis.save_fulfilled_request(allocation_id, dict(endpoint=allocation['rm_endpoint']), result)
                        continue

                if allocation["expiration"] <= time.time():
                    log.debug(f"found expired {allocation_id} with status {allocation['status']}")
                    if allocation['status'] in ['success', 'allocated']:
                        log.debug(f"deallocating")
                        allocation['status'] = 'deallocating'
                        deallocate_tasks[allocation_id] = asyncio.ensure_future(deallocate(allocation))
                        await conn.hset("allocations", allocation["allocation_id"], json.dumps(allocation))
                    else:
                        log.warning(
                            f"found IMPROPER expired {allocation['status']} allocation {allocation_id}, removing")
                        await redis.delete("allocations", allocation_id)
                else:
                    log.debug(f"job {allocation['allocation_id']} ttl: {allocation['expiration'] - int(time.time())}")

            for a_id, task in deallocate_tasks.items():
                try:
                    await task
                    await redis.delete("allocations", a_id)
                except:
                    log.error("exception deallocating, updating status to error.")
                    await redis.update_status(a_id, status='error_deallocating')
        except Exception as e:
            log.exception(f"caught exception on expires thread: {e}")

        await asyncio.sleep(10)
