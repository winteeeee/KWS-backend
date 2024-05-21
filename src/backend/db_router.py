import io
import hashlib
from datetime import date
from fastapi import APIRouter, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.factories import MySQLEngineFactory
from model.db_models import Server, Container
from model.api_models import (ApiResponse, ServersResponseDTO, ContainersResponseDTO,
                              ErrorResponse, ContainerExtensionRequestDTO)
from util.utils import validate_ssh_key
from util.logger import get_logger


db_router = APIRouter(prefix="/db")
db_connection = MySQLEngineFactory().get_instance()
backend_logger = get_logger(name='backend', log_level='INFO', save_path="./log/backend")


@db_router.get("/servers")
def server_show():
    with Session(db_connection) as session, session.begin():
        servers = session.scalars(select(Server)).all()
        server_list = []
        for server in servers:
            server_dict = server.__dict__
            del server_dict['id']
            del server_dict['_sa_instance_state']
            server_list.append(ServersResponseDTO(**server_dict).__dict__)
    return ApiResponse(status.HTTP_200_OK, server_list)


@db_router.get("/containers")
def container_show():
    with Session(db_connection) as session, session.begin():
        containers = session.scalars(select(Container)).all()
        containers_list = []
        for container in containers:
            container_dict = container.__dict__
            del container_dict['id']
            del container_dict['_sa_instance_state']
            del container_dict['password']
            containers_list.append(ContainersResponseDTO(**container_dict).__dict__)
    return ApiResponse(status.HTTP_200_OK, containers_list)


@db_router.put("/extension")
def server_renew(server_name: str = Form(...),
                 host_ip: str = Form(...),
                 end_date: str = Form(...),
                 password: str = Form(""),
                 key_file: UploadFile = Form("")):
    key_file = io.StringIO(key_file.file.read().decode('utf-8')) \
        if key_file != "" else key_file

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
                session.commit()
            except Exception as e:
                backend_logger.error(e)
                session.rollback()
                return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "백엔드 내부 오류")
        return ApiResponse(status.HTTP_200_OK, "대여 기간 연장 완료")
    else:
        return ErrorResponse(status.HTTP_400_BAD_REQUEST, "입력한 정보가 잘못됨")


@db_router.put("/container_extension")
def container_extension(container_info: ContainerExtensionRequestDTO):
    sha256 = hashlib.sha256()
    sha256.update(container_info.password.encode('utf-8'))

    with (Session(db_connection) as session):
        try:
            container = session.scalars(
                select(Container)
                .where(Container.container_name == container_info.container_name)
            ).one()

            if sha256.hexdigest() != container.password:
                return ErrorResponse(status.HTTP_400_BAD_REQUEST, "비밀번호가 맞지 않습니다.")

            split_date = container_info.end_date.split(sep='-')
            container.end_date = date(int(split_date[0]), int(split_date[1]), int(split_date[2]))
            session.add(container)
            session.commit()
        except Exception as e:
            backend_logger.error(e)
            return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "백엔드 내부 오류")

    return ApiResponse(status.HTTP_200_OK, None)
