from fastapi import APIRouter

from Model.models import ServerInfo
from Config.config import openstack_config
from OpenStack.openstack_controller import OpenStackController

router = APIRouter(prefix="/openstack")
controller = OpenStackController(cloud=openstack_config["cloud"])


@router.post("/rent")
def server_rent(server_info: ServerInfo):
    server = controller.create_server(server_info)
    floating_ip = controller.create_floating_ip()
    controller.allocate_floating_ip(server, floating_ip)

    return {"ip": floating_ip}


@router.get("/key_pair")
def get_key_pair(server_info: ServerInfo):
    # TODO 한 서버 당 이 요청은 단 한 번만 수행 가능하도록 수정
    server = controller.find_server(server_info.server_name)
    private_key, public_key = controller.find_key_pair(server=server)

    return {"private_key": private_key, "public_key": public_key}


@router.delete("/return")
def server_return(server_name: str):
    return controller.delete_server(server_name)


@router.put("/renew")
def server_renew():
    pass


@router.get("/instance")
def server_show():
    return controller.monitoring_resources()
