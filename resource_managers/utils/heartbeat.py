import asyncio
import json
import time
import logging
import aiohttp


async def send_heartbeats(rm_info, provisioner_ep):
    uri = "http://%s/api/resource_manager/heartbeat" % provisioner_ep
    logging.info(f'starting to send heartbeats with info: {rm_info} to {uri}')
    while True:
        try:
            rm_info['last_hb'] = int(time.time())
            async with aiohttp.ClientSession() as client:
                async with client.put(
                        uri, data=json.dumps(rm_info)) as resp:
                    data = await resp.json()
                    if data['status'] != 200:
                        logging.exception("sent hb failed, is allocator configure correctly?")
        except Exception as e:
            logging.exception("hb exception")
        await asyncio.sleep(15)

