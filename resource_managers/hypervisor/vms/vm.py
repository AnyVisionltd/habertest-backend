import asyncio
import uuid as libuuid


class VM(object):
    # This will be required to store/load vm info with "upgrade"
    OBJECT_VERSION = "v1"

    def __init__(self, name, num_cpus, memsize, sol_port, base_image,
                 base_image_size=None, net_ifaces=None, pcis=None, disks=None, api_version=None,
                 image=None, cloud_init_iso=None, uuid=None, allocation_id=None, requestor=None):
        self.net_ifaces = net_ifaces or []
        self.pcis = pcis or []
        self.disks = disks or []
        self.name = name
        self.num_cpus = num_cpus
        self.memsize = memsize
        self.sol_port = sol_port
        self.base_image = base_image
        self.lock = asyncio.Lock()
        self.api_version = api_version or VM.OBJECT_VERSION
        self.image = image
        self.cloud_init_iso = cloud_init_iso
        self.uuid = uuid or str(libuuid.uuid4())
        self.base_image_size = base_image_size
        self.allocation_id = allocation_id
        self.requestor = requestor

    @property
    def json(self):
        return {"net_ifaces" : self.net_ifaces,
                "pcis" : [pci.full_address for pci in  self.pcis],
                "disks" : self.disks,
                "name"  : self.name,
                "num_cpus" : self.num_cpus,
                "memsize" : self.memsize,
                "sol_port" : self.sol_port,
                "base_image" : self.base_image,
                "api_version" : self.api_version,
                "image" : self.image,
                "cloud_init_iso": self.cloud_init_iso,
                "uuid" : self.uuid,
                "base_image_size" : self.base_image_size,
                "allocation_id": self.allocation_id,
                "requestor": self.requestor}

    def __repr__(self):
        data = self.json
        data['locked'] = self.lock.locked()
        return str(data)
