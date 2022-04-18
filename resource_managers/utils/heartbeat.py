import asyncio
import json
import os
import ssl
import time
import logging
import aiohttp


async def send_heartbeats(rm_info, provisioner_ep, cert=None, key=None):
    uri = "http://%s/api/resource_manager/heartbeat" % provisioner_ep
    logging.info(f'starting to send heartbeats with info: {rm_info} to {uri}')


    if cert:
        ssl_pair = (cert, key)
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(certfile=ssl_pair[0], keyfile=ssl_pair[1])

    while True:
        try:
            rm_info['last_hb'] = int(time.time())
            if cert:
                conn = aiohttp.TCPConnector(ssl_context=ssl_context)
                client_session = aiohttp.ClientSession(connector=conn)
            else:
                client_session = aiohttp.ClientSession()
            async with client_session as client:
                async with client.put(
                        uri, data=json.dumps(rm_info)) as resp:
                    data = await resp.json()
                    if data['status'] != 200:
                        logging.exception("sent hb failed, is allocator configure correctly?")
        except Exception as e:
            logging.exception("hb exception")
        await asyncio.sleep(15)

