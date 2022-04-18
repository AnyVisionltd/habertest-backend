import asyncio
import json
import asyncio_redis


class RedisClient:
    def __init__(self, host="redis", port=6379, poolsize=10):
        self._conn = None
        self._host = host
        self._port = port
        self._pool_size = poolsize

    @property
    async def conn(self):
        if not self._conn:
            # TODO: maybe change to use aioredis library?
            # self._conn = aioredis.from_url(self._host, decode_responses=True)
            self._conn = await asyncio_redis.Pool.create(host=self._host, port=self._port, poolsize=10)
        return self._conn

    async def update_machines(self, machines):
        conn = await self.conn
        for name, conn_details in machines.items():
            conn_details.setdefault("name", name)
            conn_details.setdefault("arch", "x86_64")
            conn_details['net_ifaces'] = list()
            conn_details['net_ifaces'].append({'ip': conn_details['ip']})
            conn_details['status'] = 'available'
        await asyncio.gather(
            *[conn.hsetnx("resources", machine, json.dumps(conn_details)) for machine, conn_details in machines.items()]
        )

    async def machines(self, name=None):
        conn = await self.conn
        if name:
            res = await conn.hget("resources", name)
            try:
                res = json.loads(res)
            except (json.JSONDecodeError, TypeError):
                pass
            return res
        else:
            machines = await conn.hgetall_asdict("resources")
            # machines = await conn.hgetall("resources")
            for name, details in machines.items():
                machines[name] = json.loads(details)
            return machines

    async def update_resource(self, name, machine):
        conn = await self.conn
        await conn.hset("resources", name, json.dumps(machine))
