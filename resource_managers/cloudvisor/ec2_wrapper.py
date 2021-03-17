import re
import time
from datetime import datetime

import logging

from botocore.exceptions import ClientError


class EC2Wrapper(object):
    AWS_THREADPOOL = 20

    INSTANCE_TYPES = ["g4dn.2xlarge"]

    def __init__(self, vpc, machine_key_info, boto_ec2, id):
        self.id = id
        self.vpc = vpc
        self.boto_ec2 = boto_ec2
        self.machine_key_info = machine_key_info

    @staticmethod
    def main_cloudvisor(id):
        # The main cloudvisor run on EKS as a pod with a name generated like something in this regex:
        if re.fullmatch('root-cloudvisor-[0-9a-z]{9}-[0-9a-z]{5}-cloudvisor', id):
            return True
        return False

    @staticmethod
    def dict_to_filter(filter_dict):
        '''
        This gets a dict like {key: val, key2: val2} and returns a list of filters like:
        [{Name: key, Values: [val]}, {Name: key2, Values: [val2]}]
        '''
        res = list()
        for k, v in filter_dict.items():
            res.append({"Name": k, 'Values': [v] if type(v) is not list else v})
        return res

    @staticmethod
    def dict_to_tags(tag_dict):
        res = list()
        for k, v in tag_dict.items():
            res.append({"Key": k, "Value": v})
        return res

    @staticmethod
    def _automation_filters():
        return EC2Wrapper.dict_to_filter({'tag:purpose': "automation"})

    @staticmethod
    def load_vpc_subnets(boto_ec2, vpc_id):
        filters = [{'Name': 'vpc-id', 'Values': [vpc_id]}]
        return boto_ec2.subnets.filter(Filters=filters)

    @staticmethod
    def load_vpc(boto_ec2, vpc_id):
        vpcs = list(boto_ec2.vpcs.filter(VpcIds=[vpc_id]))
        if not vpcs:
            raise Exception("Existing VPC must be specified")
        return vpcs[0]

    @staticmethod
    def _tags_dict(instance):
        return {tag['Key']: tag['Value'] for tag in instance.tags}

    @staticmethod
    def _tagged_as_automation(instance):
        tags = EC2Wrapper._tags_dict(instance)
        return tags.get('purpose') == 'automation'

    def find_image_by_version_tag(self, version_tag):
        images = list(
            self.images(self.dict_to_filter({"tag:infra_version": version_tag})).all())
        assert len(images) == 1, f"{images} images match version {version_tag}, check base_image_tag field of request"
        return images[0]

    @staticmethod
    def load_key_pair(ec2, keyname):
        keys = [k for k in ec2.key_pairs.filter(KeyNames=[keyname])]
        if len(keys) != 1:
            raise Exception(f"Length of the keys is {len(keys)}")
        return keys[0]

    @staticmethod
    def load_machine_key_info(ec2, keyname, pem_file):
        with open(pem_file, 'r') as f:
            pem_content = f.read()
        return {"pair": EC2Wrapper.load_key_pair(ec2, keyname),
                "pem": pem_content}

    @staticmethod
    def _automation_tag():
        return {'Key': 'purpose', 'Value': 'automation'}

    @staticmethod
    def _allocation_tag(vm):
        return {'Key': 'allocation_id', 'Value': vm.allocation_id}

    @staticmethod
    def _default_tags(vm):
        return [EC2Wrapper._automation_tag(), EC2Wrapper._allocation_tag(vm)]

    def _instance_tags(self, vm):
        requestor_tags = {f'requestor:{k}': v[:255] for k, v in vm.requestor.items()}
        tags = [{'Key': k, 'Value': str(v)[:255]} for k, v in vm.json.items()] + \
               [EC2Wrapper._automation_tag()] + \
               [{'Key': 'Name',
                 'Value': getattr(vm, "Name", f'automation-infra-{datetime.now().strftime("%Y_%m_%d__%H%M")}')}] + \
               self.dict_to_tags({**{"cloudvisor_id": self.id}, **requestor_tags})

        return tags

    @staticmethod
    def _allocation_id_from_instance(instance):
        tags = EC2Wrapper._tags_dict(instance)
        return tags.get('allocation_id')

    def _create_security_group(self, vm):
        allocating_ip = vm.client_external_ip
        sg_name = f"automation_allocation_{vm.allocation_id}"
        tags = EC2Wrapper._default_tags(vm) + [{'Key': 'Name', 'Value': sg_name}] + \
               [{'Key': 'creation', 'Value': str(time.time())}]

        security_group = self.boto_ec2.create_security_group(Description=vm.allocation_id,
                                                             GroupName=vm.allocation_id,
                                                             VpcId=self.vpc.id,
                                                             TagSpecifications=[{'ResourceType': 'security-group',
                                                                                 "Tags": tags}])

        ssh_any_host_rule = {'IpProtocol': 'tcp', 'ToPort': 22, 'FromPort': 22,
                             'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                             'Ipv6Ranges': [{'CidrIpv6': '::/0'}]}
        all_traffic_in_security_group = {'IpProtocol': '-1',
                                         'UserIdGroupPairs': [{'VpcId': self.vpc.id, 'GroupId': security_group.id}]}
        all_traffic_in_vpc = {'IpProtocol': '-1', 'IpRanges': [{'CidrIp': f'{self.vpc.cidr_block}'}]}

        all_from_peer = {'IpProtocol': '-1', 'IpRanges': [{'CidrIp': '%s/32' % allocating_ip}]}
        allowed_rules = [all_traffic_in_security_group, all_from_peer, ssh_any_host_rule, all_traffic_in_vpc]
        security_group.authorize_ingress(IpPermissions=allowed_rules)

        return security_group

    def _find_security_group(self, allocation_id):
        filters = [{'Name': 'vpc-id', 'Values': [self.vpc.id]},
                   {'Name': 'group-name', 'Values': [allocation_id]}]
        return next(iter(self.boto_ec2.security_groups.filter(Filters=filters)))

    def _get_or_create_security_group(self, vm):
        try:
            return self._find_security_group(vm.allocation_id)
        except StopIteration:
            logging.info(f"Did not find security group for {vm.allocation_id} creating")
            return self._create_security_group(vm)

    def _delete_security_group(self, allocation_id):
        # Note that this will not work for more than single VM
        logging.info(f'Going to delete security group for VM from allocation {allocation_id}')
        sg = self._find_security_group(allocation_id)
        sg.delete()

    def check_allocate(self, vm):
        '''Placeholder'''
        return True

    def allocate(self, vm):
        logging.info(f"allocating vm: {vm.json}")
        net_id = vm.net_ifaces[0]['subnet']

        key_name = self.machine_key_info['pair'].key_name
        sg = self._get_or_create_security_group(vm)

        network = {'DeviceIndex': 0,
                   'DeleteOnTermination': True,
                   'Description': vm.allocation_id,
                   'Groups': [sg.id],
                   'SubnetId': net_id,
                   'AssociatePublicIpAddress': True
                   }

        image_version_tag = vm.base_image
        image = self.find_image_by_version_tag(image_version_tag)

        start = time.time()
        instance = self.boto_ec2.create_instances(
            ImageId=image.id,
            MinCount=1, MaxCount=1,
            KeyName=key_name,
            InstanceType=vm.instance_type,
            NetworkInterfaces=[network],
            TagSpecifications=[{"ResourceType": "instance",
                                "Tags": self._instance_tags(vm)}]
        )[0]
        logging.info(f"{instance.id}: create_instance time: {time.time() - start}")
        instance.wait_until_exists()
        logging.info(f"{instance.id}: exists elapsed time: {time.time() - start}s")
        instance.wait_until_running()
        logging.info(f"{instance.id}: until running elapsed: {time.time() - start}s")
        instance.reload()
        logging.info(f"{instance.id}: after reload elapsed: {time.time() - start}s")
        vm.instance_id = instance.id
        instance.num_cpus = instance.cpu_options['CoreCount'] * instance.cpu_options['ThreadsPerCore']
        vm.net_ifaces[0]['ip'] = instance.public_ip_address
        logging.info(f"successfully allocated vm: {vm.json}")
        return instance

    def destroy(self, instance_ids):
        logging.info(f"destroying instance ids  {instance_ids}")
        machines = self.describe(instance_ids)
        logging.info("found machines.. destroying")
        start = time.time()
        for machine in machines:
            allocation_id = EC2Wrapper._allocation_id_from_instance(machine)
            if not EC2Wrapper._tagged_as_automation(machine):
                raise Exception(
                    f"Selected machine is not an automation machine {machine.id} tags {EC2Wrapper._tag_in_machine(machine)}")
            logging.info(f"Terminating machine {machine.id} allocation {allocation_id}")
            machine.terminate()
        logging.info(f"terminate elapsed: {time.time() - start}")

    def destroy_all(self):
        logging.info("destroying all instances")
        actives = self.list_active()
        instance_ids = [active.id for active in actives.all()]
        self.destroy(instance_ids)
        logging.info("destroyed all successfully!")

    def list(self, **kwargs):
        '''
        kwargs:
        Filters=list(dict):
         {
            'Name': 'string',
            'Values': [
                'string',
            ]
        }
        full api:
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.ServiceResource.instances
        '''
        filters = self._automation_filters()
        received_filters = kwargs.pop("Filters", [])
        received_filters = [received_filters] if type(received_filters) is not list else received_filters
        filters.extend(received_filters)
        instances = self.boto_ec2.instances.filter(
            Filters=filters,
            **kwargs
        )
        return instances

    def list_active(self):
        instances = self.list()
        filters = self.dict_to_filter(
            {'instance-state-name': ['pending', 'running', 'stopping', 'stopped']})
        return instances.filter(Filters=filters)

    def images(self, filters=[]):
        return self.boto_ec2.images.filter(Filters=self._automation_filters()).filter(Filters=filters)

    def describe(self, instance_ids):
        instance_ids = [instance_ids] if type(instance_ids) is not list else instance_ids
        instances = self.list(InstanceIds=instance_ids)
        return instances

    def _automation_security_groups(self):
        return self.boto_ec2.security_groups.filter(Filters=self._automation_filters())

    def delete_dangling_security_groups(self):
        for security_group in self._automation_security_groups():
            if (time.time() - float(self._tags_dict(security_group).get('creation', 0))) < 5*60:
                continue
            security_group.reload()
            if not security_group.get_available_subresources():
                try:
                    security_group.delete()
                except ClientError:
                    logging.warning(f"security group {security_group} has dependencies")
