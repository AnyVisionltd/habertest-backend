import getpass
import socket
import uuid

import requests


RM_EP = "http://localhost:9080"


def test_happy_flow():
    res = requests.get(f'{RM_EP}')
    assert res.status_code == 200
    res = requests.get(f'{RM_EP}/vms')
    assert res.status_code == 200
    machine_reqs = {"base_image": 'ami-0e7c10ea30d385335', "instance_type": 'g4dn.2xlarge',
                    "client_external_ip": requests.get("http://checkip.amazonaws.com/").text.strip(),
                    "requestor": dict(hostname=socket.gethostname(), username=getpass.getuser(),
                                            ip=socket.gethostbyname(socket.gethostname()),
                                            external_ip=requests.get("http://checkip.amazonaws.com/").text.strip())}
    create_res = requests.post(f'{RM_EP}/vms', json=machine_reqs)
    assert create_res.status_code == 200
    instance_id = create_res.json()['machine']['instance_id']
    allocation_id = create_res.json()['machine']['allocation_id']
    alloc_res = requests.get(f'{RM_EP}/allocations/{allocation_id}')
    assert alloc_res.status_code == 200
    status_res = requests.get(f'{RM_EP}/vms/{instance_id}')
    assert status_res.status_code == 200
    delete_res = requests.delete(f'{RM_EP}/vms/{instance_id}')
    assert delete_res.status_code == 200

    fulfill_data = {'demands': {'host': {}},
                    'allocation_id': str(uuid.uuid4()),
                    'requestor': dict(hostname=socket.gethostname(), username=getpass.getuser(),
                                      ip=socket.gethostbyname(socket.gethostname()), external_ip=requests.get("http://checkip.amazonaws.com/").text.strip())
                    }

    check_fulfill_res = requests.post(f'{RM_EP}/fulfill/theoretically',
                                      json=fulfill_data)
    assert check_fulfill_res.status_code == 200

    fulfill_now_res = requests.post(f'{RM_EP}/fulfill/now', json=fulfill_data)
    assert fulfill_now_res.status_code == 200
    instance_id = fulfill_now_res.json()['info'][0]['instance_id']

    deallocate_res = requests.delete(f'{RM_EP}/deallocate/{instance_id}')
    assert deallocate_res.status_code == 200
