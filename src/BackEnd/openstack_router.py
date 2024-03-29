from fastapi import APIRouter

from Model.models import ServerInfo
from Config.config import openstack_config
from OpenStack.openstack_controller import OpenStackController

router = APIRouter(prefix="/openstack")
controller = OpenStackController(cloud=openstack_config["cloud"])


@router.post("/rent")
def server_rent(server_info: ServerInfo):
    server = controller.create_server(server_info)
    floating_ip = controller.allocate_floating_ip(server)
    # TODO 키 페어 파일 전달

    return {"private_key": "foo", "ip": floating_ip}


@router.delete("/return")
def server_return():
    pass


@router.put("/renew")
def server_renew():
    pass


@router.get("/instance")
def server_show():
    pass
