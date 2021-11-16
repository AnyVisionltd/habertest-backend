import json
from builtins import getattr

from cloudvisor.ec2_wrapper import EC2Wrapper
from common import vm as vm_base


class VM(vm_base.VM):
    def __init__(self, base_image, client_external_ip, num_gpus,  user='ubuntu', instance_type=None, pem_key_string=None, name=None, num_cpus=0, memsize=0,
                 net_ifaces=None, api_version=None, uuid=None, allocation_id=None, requestor=dict()):
        super().__init__(name=name, num_cpus=num_cpus, memsize=memsize, base_image=base_image,
                         net_ifaces=net_ifaces, api_version=api_version, uuid=uuid, allocation_id=allocation_id,
                         requestor=requestor)
        self.instance_id = None
        self.state = None
        self.num_cpus = None
        self.num_gpus = num_gpus
        self.tags = dict()
        self.client_external_ip = client_external_ip
        self.instance_type = instance_type
        self.user = user
        self.pem_key_string = pem_key_string

    @classmethod
    def from_aws_instance(cls, instance):
        tags = EC2Wrapper._tags_dict(instance)
        vm = cls(base_image=instance.image.image_id,
                   client_external_ip=tags.get('requestor:external_ip', None) or tags.get('client_external_ip', None),
                   instance_type=instance.instance_type,
                   user=tags.get('user', None),
                   allocation_id=tags.get('allocation_id', None),
                   name=instance.id,
                   num_gpus=None,
                   net_ifaces=[dict(ip=instance.public_ip_address)]
                   )
        vm.tags = tags
        vm.state = instance.state['Name']
        return vm

    @property
    def json(self):
        result = super().json
        result.update({'client_external_ip': self.client_external_ip,
                       'instance_type' : self.instance_type,
                       'instance_id': self.instance_id,
                       'user': self.user,
                       'pem_key_string': self.pem_key_string,
                       'tags': self.tags,
                       'state': self.state})
        return result
    
    @property
    def allocating_ip(self):
        return getattr(self, "external_ip")

    def __repr__(self):
        data = self.json
        return str(data)

    @property
    def long_lasting(self, ):
        return self.tags.get("requestor:long_lasting", False)