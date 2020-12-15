import requests


def create(resource_manager, data):
    return requests.post("http://%s/vms" % resource_manager, json=data)


def delete(resource_manager, vm_name):
    return requests.delete(f"http://{resource_manager}/vms/{vm_name}")


def list_images(resource_manager):
    return requests.get(f"http://{resource_manager}/images")


def list_vms(resource_manager):
    return requests.get(f"http://{resource_manager}/vms")


def update_vm(resource_manager, vm_name, status):
    return requests.post(f"http://{resource_manager}/vms/{vm_name}/status", json=status)


def vm_info(resource_manager, vm_name):
    return requests.get("http://%s/vms/%s" % (resource_manager, vm_name))


def resources(resource_manager):
    return requests.get(f"http://{resource_manager}/resources")
