import asyncio

from common.vm import VM as baseVM


class VM(baseVM):
    def __init__(self, name, num_cpus, memsize, base_image, user='root', password='root', sol_port=None,
                 base_image_size=None, net_ifaces=None, pcis=None, disks=None, api_version=None,
                 image=None, cloud_init_iso=None, uuid=None, allocation_id=None, requestor=dict(), **kwargs):
        super().__init__(name, num_cpus, memsize, base_image, net_ifaces, api_version, uuid, allocation_id, requestor)
        self.pcis = pcis or []
        self.disks = disks or []
        self.sol_port = sol_port
        self.lock = asyncio.Lock()
        self.image = image
        self.cloud_init_iso = cloud_init_iso
        self.base_image_size = base_image_size
        self.user = user
        self.password = password

    @property
    def json(self):
        res = super().json
        additional = {
            "net_ifaces": self.net_ifaces,
            "pcis": [pci.full_address for pci in self.pcis],
            "disks": self.disks,
            "sol_port": self.sol_port,
            "cloud_init_iso": self.cloud_init_iso,
            "base_image_size": self.base_image_size,
            "user": self.user,
            "password": self.password,
        }
        res.update(additional)
        return res

    def __repr__(self):
        data = self.json
        data['locked'] = self.lock.locked()
        return str(data)
