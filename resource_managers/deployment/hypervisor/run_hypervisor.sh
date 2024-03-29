#!/bin/bash
set -e

# Absolute path to this script
SCRIPT=$(readlink -f "$0")
# Absolute path to the script directory
BASEDIR=$(dirname "$SCRIPT")
# ROOT DIR
ROOT_DIR=${BASEDIR%/*/*}

BASE_IMAGE_DIR="${BASE_IMAGE_DIR:-/ssd/vms/images}"
ROOT_IMAGES_DIR="${ROOT_IMAGES_DIR:-/ssd/vms/root_images}"
SSD_IMAGES_DIR="${SSD_IMAGES_DIR:-/ssd/vms/ssd_images}"
HDD_IMAGES_DIR="${HDD_IMAGES_DIR:-/storage/vms/hdd_images}"
PROJECT_DIR="${PROJECT_DIR:-$ROOT_DIR}"
CONFIG_FILE="${CONFIG_FILE:-$PROJECT_DIR/hypervisor/config/hypervisor.yaml}"
MAX_VMS="${MAX_VMS:-1}"
LOG_LEVEL="${LOG_LEVEL:-DEBUG}"
DEFAULT_NIC=$(ip route show default | head -1  | awk '{print $5}')
PARAVIRT_NET_DEVICE="${PARAVIRT_NET_DEVICE:-$DEFAULT_NIC}"
SOL_PORT="${SOL_PORT:-10000}"
HOSTNAME=$(hostname)
KERNEL_LIBS=/lib/modules/$(uname -r)
LIBVIRT_SOCK=/var/run/libvirt/libvirt-sock
HABERTEST_PROVISIONER_ADDRESS="localhost:8080"
SEND_HEARTBEATS=0


python3 ${PROJECT_DIR}/hypervisor/tools/config_hypervisor.py --max-vms ${MAX_VMS}

files_sum=$(find ${PROJECT_DIR}/ ${PROJECT_DIR}/Dockerfile.hypervisor -type f -exec md5sum {} \; | sort -k 2 | md5sum | awk {'print $1'} | awk '{print substr($1,1,12)}')
HYPERVISOR_DOCKER_TAG="${HYPERVISOR_DOCKER_TAG:-$files_sum}"

if [[ "$(docker images -q "hypervisor:${HYPERVISOR_DOCKER_TAG}" 2> /dev/null)" == "" ]]; then
  docker build --network=host -t hypervisor:${HYPERVISOR_DOCKER_TAG} -f "Dockerfile.hypervisor" "${PROJECT_DIR}"
fi

MOUNTS=("$ROOT_IMAGES_DIR:$ROOT_IMAGES_DIR"
        "${BASE_IMAGE_DIR}:${BASE_IMAGE_DIR}:ro"
        "${SSD_IMAGES_DIR}:${SSD_IMAGES_DIR}"
        "${HDD_IMAGES_DIR}:${HDD_IMAGES_DIR}"
        "${LIBVIRT_SOCK}:${LIBVIRT_SOCK}"
        "/dev:/dev"
        "${CONFIG_FILE}:/root/config.yaml:ro"
        "${KERNEL_LIBS}:${KERNEL_LIBS}")

mounts_cmd=""
for i in "${MOUNTS[@]}"
do
    mounts_cmd+=" -v $i "
done
mounts_cmd+=" "

params="--config=/root/config.yaml --images-dir=${BASE_IMAGE_DIR} --run-dir=${ROOT_IMAGES_DIR} \
--ssd-dir=${SSD_IMAGES_DIR} --hdd-dir=${HDD_IMAGES_DIR} --log-level=${LOG_LEVEL} --max-vms=${MAX_VMS} \
--paravirt-net-device=${PARAVIRT_NET_DEVICE} --sol-port=${SOL_PORT} --server-name=${HOSTNAME}"

if [[ $SEND_HEARTBEATS == 1 ]]
then
  params+=" --provisioner=${HABERTEST_PROVISIONER_ADDRESS}"
fi

docker stop --time=30 $(docker ps -aq --filter name=hypervisor) 2> /dev/null || true
docker rm $(docker ps -aq --filter name=hypervisor) 2> /dev/null || true

docker run -d --net=host --privileged --restart=always --log-driver=syslog --log-opt tag=HYPERVISOR \
${mounts_cmd} --name hypervisor -e HABERTEST_PROVISIONER_ADDRESS=${HABERTEST_PROVISIONER_ADDRESS} hypervisor:${HYPERVISOR_DOCKER_TAG} ${params}
