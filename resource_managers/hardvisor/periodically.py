import asyncio
import logging
import ssl
import aiohttp


class Cleaner:
    def __init__(self, provisioner_ip, manager, cert=None, key=None):
        self.provisioner_ep = provisioner_ip
        self.manager = manager
        self.ssl_cert = (cert, key)
        if cert:
            self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.ssl_context.load_cert_chain(certfile=self.ssl_cert[0], keyfile=self.ssl_cert[1])

    async def clean_dangling_hardware(self):
        while True:
            try:
                logging.info("cleaning dangling hardware..")
                await self.do_clean_dangling_hardware()
                logging.info("done cleaning dangling hardware")
            except Exception as e:
                logging.exception("Caught exception in clean periodically: ")
            await asyncio.sleep(60 * 1)

    async def active_allocation_ids(self):
        uri = "http://%s/api/jobs" % self.provisioner_ep
        logging.info(f"getting allocations from {uri}")
        conn = aiohttp.TCPConnector(ssl_context=self.ssl_context)
        async with aiohttp.ClientSession(connector=conn) as client:
            async with client.get(
                    uri) as resp:
                data = await resp.json()
                if data['status'] != 200:
                    raise Exception(f"couldnt get jobs from ep: {uri}")
                active_allocation_ids = set(allocation['allocation_id'] for allocation in data['data'])
                return active_allocation_ids

    async def do_clean_dangling_hardware(self):
        """
        In the case where a machine was meant to be released but for some reason it wasn't updated in redis as released..
        So periodically check in with provisioner that all in_use machines are really provisioned and not dangling...
        """
        active_allocation_ids = await self.active_allocation_ids()
        machines = await self.manager.all_machines()
        for machine in machines.values():
            if machine.get('status', None) == "in_use":
                if machine.get('allocation_id', None) not in active_allocation_ids:
                    logging.warning(f"found dangling machine: {machine}.. releasing")
                    await self.manager.release(machine['name'])

