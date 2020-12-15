import uuid as libuuid


class VM(object):
    # This will be required to store/load vm info with "upgrade"
    OBJECT_VERSION = "v1"

    def __init__(self, name, num_cpus, memsize, base_image, net_ifaces=None, api_version=None,
                 uuid=None, allocation_id=None, requestor=dict()):
        self.net_ifaces = net_ifaces or []
        self.name = name
        self.num_cpus = num_cpus
        self.memsize = memsize
        self.base_image = base_image
        self.api_version = api_version or self.OBJECT_VERSION
        self.uuid = uuid or str(libuuid.uuid4())
        self.allocation_id = allocation_id
        self.requestor = requestor
        self.image = None

    @property
    def json(self):
        return {"net_ifaces": self.net_ifaces,
                "name": self.name,
                "num_cpus": self.num_cpus,
                "memsize": self.memsize,
                "base_image": self.base_image,
                "api_version": self.api_version,
                "image": self.image,
                "uuid": self.uuid,
                "allocation_id": self.allocation_id,
                "requestor": self.requestor}

    def __repr__(self):
        data = self.json
        return str(data)
