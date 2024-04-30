from fastapi import APIRouter

from config.config import openstack_config
from database.ServerDAO import ServerDAO
from database.factories import MySQLEngineFactory
from model.db_models import Server
from model.http_models import ServerInfo
from openStack.openstack_controller import OpenStackController
from datetime import datetime

router = APIRouter(prefix="/openstack")
controller = OpenStackController(cloud=openstack_config["cloud"])
serverDAO = ServerDAO(MySQLEngineFactory())


@router.post("/rent")
def server_rent(server_info: ServerInfo):
    server = controller.create_server(server_info)
    floating_ip = controller.create_floating_ip()
    controller.allocate_floating_ip(server, floating_ip)

    flavor = controller.find_flavor(flavor_name=server_info.flavor_name)
    serverDAO.save(Server(
        user_name=server_info.user_name,
        server_name=server_info.server_name,
        start_date=server_info.start_date,
        end_date=server_info.end_date,
        vcpu=flavor.vcpus,
        ram=flavor.ram,
        floating_ip=floating_ip
    ))

    return {"ip": floating_ip}


@router.get("/key_pair")
def get_key_pair(server_info: ServerInfo):
    # TODO 한 서버 당 이 요청은 단 한 번만 수행 가능하도록 수정
    server = controller.find_server(server_info.server_name)
    private_key, public_key = controller.find_key_pair(server=server)

    return {"private_key": private_key, "public_key": public_key}


@router.get("/instance")
def server_show():
    servers = serverDAO.find_all()
    return servers


@router.get("/resources")
def servers_resource():
    return controller.monitoring_resources()


@router.delete("/return")
def server_return(server_name: str,
                  host_name: str,
                  user_name: str,
                  private_key: bytes = None,
                  password: str = None):
    if controller.validate_ssh_key(host_name=host_name,
                                   user_name=user_name,
                                   private_key=private_key,
                                   password=password):
        server = serverDAO.find_by_server_name(server_name)
        serverDAO.delete(server)
        controller.delete_server(server_name)


@router.put("/renew")
def server_renew(server_name: str,
                 new_end_date: datetime,
                 host_name: str,
                 user_name: str,
                 private_key: bytes = None,
                 password: str = None):
    if controller.validate_ssh_key(host_name=host_name,
                                   user_name=user_name,
                                   private_key=private_key,
                                   password=password):
        server = serverDAO.find_by_server_name(server_name)
        server.end_date = new_end_date
        serverDAO.save(server)
