import io
from datetime import date
from fastapi import APIRouter, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.factories import MySQLEngineFactory
from model.db_models import Server
from model.api_models import ServerCreateRequestDTO
from openStack.openstack_controller import OpenStackController
from util.utils import validate_ssh_key

router = APIRouter(prefix="/openstack")
controller = OpenStackController()
db_connection = MySQLEngineFactory().get_instance()


@router.post("/rental")
def server_rent(server_info: ServerCreateRequestDTO):
    with Session(db_connection) as session:
        session.begin()
        try:
            server, private_key = controller.create_server(server_info)
            floating_ip = controller.allocate_floating_ip(server)
            flavor = controller.find_flavor(flavor_name=server_info.flavor_name)

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
        except:
            session.rollback()
            controller.delete_server(server, floating_ip)
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        session.commit()
        
    name = f'{server_info.server_name}_keypair.pem' if private_key != "" else ""
    return {"name": name, "data": private_key}


@router.get("/servers")
def server_show():
    with Session(db_connection) as session, session.begin():
        servers = session.scalars(select(Server)).all()
        server_list = []
        for server in servers:
            server_dict = server.__dict__
            server_list.append({
                'user_name': server_dict['user_name'],
                'server_name': server_dict['server_name'],
                'floating_ip': server_dict['floating_ip'],
                'start_date': server_dict['start_date'],
                'end_date': server_dict['end_date']
            })
        return server_list


@router.get("/image_list")
def image_list_show():
    try:
        images = controller.find_images()
    except:
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    image_list = []
    for image in images:
        image_list.append({
            "name": image.name
        })

    return image_list


@router.get("/flavor_list")
def flavor_list_show():
    try:
        flavors = controller.find_flavors()
    except:
        return status.HTTP_500_INTERNAL_SERVER_ERROR

    flavor_list = []
    for flavor in flavors:
        flavor_list.append({
            "name": flavor.name,
            "cpu": flavor.vcpus,
            "ram": flavor.ram,
            "disk": flavor.disk
        })

    return sorted(flavor_list, key=lambda f: (f['cpu'], f['ram'], f['disk']))


@router.delete("/return")
async def server_return(server_name: str = Form(...),
                        host_ip: str = Form(...),
                        password: str = Form(""),
                        key_file: UploadFile = Form("")):
    key_file = io.StringIO(key_file.file.read().decode('utf-8')) if key_file != "" else key_file

    if validate_ssh_key(host_name=host_ip,
                        user_name=server_name,
                        private_key=key_file,
                        password=password):
        with Session(db_connection) as session:
            session.begin()

            try:
                server = session.scalars(
                    select(Server)
                    .where(Server.server_name == server_name)
                ).one()
                session.delete(server)
                controller.delete_server(server_name, host_ip)
            except:
                session.rollback()
                return status.HTTP_500_INTERNAL_SERVER_ERROR
            session.commit()
    else:
        return status.HTTP_400_BAD_REQUEST


@router.put("/extension")
def server_renew(server_name: str = Form(...),
                 host_ip: str = Form(...),
                 end_date: str = Form(...),
                 password: str = Form(""),
                 key_file: UploadFile = Form("")):
    key_file = io.StringIO(key_file.file.read().decode('utf-8')) if key_file != "" else key_file

    if validate_ssh_key(host_name=host_ip,
                        user_name=server_name,
                        private_key=key_file,
                        password=password):
        with Session(db_connection) as session:
            session.begin()
            try:
                server = session.scalars(
                    select(Server)
                    .where(Server.server_name == server_name)
                ).one()
                split_date = end_date.split(sep='-')
                server.end_date = date(int(split_date[0]), int(split_date[1]), int(split_date[2]))
                session.add(server)
            except:
                session.rollback()
                return status.HTTP_500_INTERNAL_SERVER_ERROR
            session.commit()
    else:
        return status.HTTP_400_BAD_REQUEST
