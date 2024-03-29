import pytest
from hypervisor.vms import storage, vm_manager, libvirt_wrapper, dhcp_handlers, cloud_init, image_store
from hypervisor.vms import physical_vm as vm
import mock


@pytest.fixture
def mock_libvirt():
    return mock.Mock(spec=libvirt_wrapper.LibvirtWrapper)


@pytest.fixture
def mock_image_store():
    return mock.AsyncMock(spec=image_store.ImageStore)

@pytest.fixture
def mock_nbd_provisioner():
    return mock.Mock(spec=storage.NBDProvisioner)

@pytest.fixture
def mock_cloud_init():
    return mock.Mock(spec=cloud_init.CloudInit)

@pytest.fixture
def mock_dhcp_handler():
    return mock.Mock(spec=dhcp_handlers.DHCPManager)

@pytest.mark.asyncio
async def test_network_info_not_failing(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler):
    tested = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler)
    mock_libvirt.dhcp_lease_info.side_effect = Exception("exception")
    mock_libvirt.status.return_value = "on"

    vm_images = [{"serial": "s1",
                  "device_name": "dev1",
                  "image" : "image",
                  "type" : "hdd",
                  "size" : 10}]
    machine = vm.VM(name="name", num_cpus=1, memsize=1,
                    net_ifaces=[], sol_port=2,
                    base_image='image',
                    disks=vm_images)
    info = await tested.info(machine)
    assert info['status'] == 'on'


@pytest.mark.asyncio
async def test_load_vm_info(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler):
    tested = vm_manager.VMManager(event_loop, mock_libvirt, mock_image_store, mock_nbd_provisioner, mock_cloud_init, mock_dhcp_handler)
    vm_images = [{"serial": "s1",
                  "device_name": "dev1",
                  "image" : "image",
                  "type" : "hdd",
                  "size" : 10}]
    machine = dict(name="name", num_cpus=1, memsize=1,
                         net_ifaces=[], sol_port=2,
                         base_image='image',
                         disks=vm_images)
    mock_libvirt.load_lab_vms.return_value = [machine, machine]
    vms = await tested.load_vms_data()
    assert len(vms) == 2
    assert vms[0] == machine
    assert vms[1] == machine

