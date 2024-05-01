from datetime import date
from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.factories import MySQLEngineFactory
from model.db_models import Server
from model.http_models import ServerDTOForCreate, ServerDTOForUpdate, ServerDTOForDelete
from openStack.openstack_controller import OpenStackController

router = APIRouter(prefix="/openstack")
controller = OpenStackController()
db_connection = MySQLEngineFactory().get_instance()

# TODO 1. 하루에 한 번씩 DB에서 end_date를 스캔하여 end_date가 지난 인스턴스 삭제
# TODO 2. 로깅 구현
# TODO 3. 키페어 프론트에서 구현되면 테스트 해보기


@router.post("/rental")
def server_rent(server_info: ServerDTOForCreate):
    server = controller.create_server(server_info)
    floating_ip = controller.allocate_floating_ip(server)

    flavor = controller.find_flavor(flavor_name=server_info.flavor_name)
    with Session(db_connection) as session, session.begin():
        server = Server(
            user_name=server_info.user_name,
            server_name=server_info.server_name,
            start_date=server_info.start_date,
            end_date=server_info.end_date,
            vcpu=flavor.vcpus,
            ram=flavor.ram,
            floating_ip=floating_ip
        )
        session.add(server)
        session.commit()

    return {"ip": floating_ip}


@router.get("/servers")
def server_show():
    with Session(db_connection) as session, session.begin():
        servers = session.scalars(select(Server)).all()
        return servers


@router.get("image_list")
def image_list_show():
    images = controller.find_images()
    image_list = []
    for image in images:
        image_list.append({
            "name": image.name
        })

    return image_list


@router.get("/flavor_list")
def flavor_list_show():
    flavors = controller.find_flavors()
    flavor_list = []
    for flavor in flavors:
        flavor_list.append({
            "name": flavor.name,
            "cpu": flavor.vcpus,
            "ram": flavor.ram,
            "disk": flavor.disk
        })

    return flavor_list


@router.delete("/return")
def server_return(server_info: ServerDTOForDelete):
    if controller.validate_ssh_key(host_name=server_info.host_ip,
                                   user_name=server_info.server_name,
                                   private_key=None,
                                   password=server_info.password):
        with Session(db_connection) as session, session.begin():
            server = session.scalars(
                select(Server)
                .where(Server.server_name == server_info.server_name)
            ).one()
            session.delete(server)
            session.commit()
        controller.delete_server(server_info.server_name)


@router.put("/extension")
def server_renew(server_info: ServerDTOForUpdate):
    if controller.validate_ssh_key(host_name=server_info.host_ip,
                                   user_name=server_info.server_name,
                                   private_key=None,
                                   password=server_info.password):
        with Session(db_connection) as session, session.begin():
            server = session.scalars(
                select(Server)
                .where(Server.server_name == server_info.server_name)
            ).one()
            split_date = server_info.end_date.split(sep='-')
            server.end_date = date(int(split_date[0]), int(split_date[1]), int(split_date[2]))
            session.add(server)
            session.commit()
