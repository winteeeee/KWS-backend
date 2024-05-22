import hashlib
from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from openStack.openstack_controller import OpenStackController
from database.factories import MySQLEngineFactory
from model.api_models import ContainerCreateRequestDTO, ErrorResponse, ApiResponse, ContainerReturnRequestDTO
from model.db_models import Container, Server
from util.utils import create_env_dict
from util.logger import get_logger
from util.backend_utils import network_isolation, network_delete
from config.config import openstack_config


container_router = APIRouter(prefix="/container")
controller = OpenStackController()
db_connection = MySQLEngineFactory().get_instance()
backend_logger = get_logger(name='backend', log_level='INFO', save_path="./log/backend")


@container_router.post("/rental")
def rental(container_info: ContainerCreateRequestDTO):
    if controller.find_container(container_info.container_name) is not None:
        return ErrorResponse(status.HTTP_400_BAD_REQUEST, "컨테이너 이름 중복")

    with Session(db_connection) as session:
        try:
            if container_info.network_name is None:
                network_name = openstack_config['external_network']
            else:
                network_name = container_info.network_name
                # 네트워크 분리 적용
                if controller.find_network(container_info.network_name) is None:
                    network_isolation(controller=controller,
                                      backend_logger=backend_logger,
                                      network_name=container_info.network_name,
                                      subnet_cidr=container_info.subnet_cidr)

            container = controller.create_container(container_name=container_info.container_name,
                                                    image_name=container_info.image_name,
                                                    network_name=network_name,
                                                    env=create_env_dict(container_info.env),
                                                    cmd=container_info.cmd)

            sha256 = hashlib.sha256()
            sha256.update(container_info.password.encode('utf-8'))
            container = Container(
                user_name=container_info.user_name,
                container_name=container_info.container_name,
                start_date=container_info.start_date,
                end_date=container_info.end_date,
                image_name=container_info.image_name,
                password=sha256.hexdigest(),
                ip=list(container.addresses.values())[0][0]['addr'],
                port=str(container.ports[0]),
                network_name=network_name,
                node_name=container.host
            )

            session.add(container)
            session.commit()
        except Exception as e:
            backend_logger.error(e)
            session.rollback()
            controller.delete_container(container_info.container_name)
            return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "백엔드 내부 오류")

        return ApiResponse(status.HTTP_201_CREATED, None)


@container_router.delete("/return")
def container_return(container_info: ContainerReturnRequestDTO):
    sha256 = hashlib.sha256()
    sha256.update(container_info.password.encode('utf-8'))

    with Session(db_connection) as session:
        try:
            container = session.scalars(
                select(Container)
                .where(Container.container_name == container_info.container_name)
            ).one()

            if sha256.hexdigest() != container.password:
                return ErrorResponse(status.HTTP_400_BAD_REQUEST, "비밀번호가 맞지 않습니다.")

            network_name = container.network_name
            controller.delete_container(container_info.container_name)
            session.delete(container)
            session.commit()

            if (network_name != openstack_config['external_network'] and
                network_name != openstack_config['default_internal_network'] and
                session.scalars(select(Server).where(Server.network_name == network_name)).one_or_none() is None and
                    session.scalars(select(Container).where(Container.network_name == network_name)).one_or_none() is None):
                network_delete(controller=controller,
                               backend_logger=backend_logger,
                               network_name=network_name)

        except Exception as e:
            backend_logger.error(e)
            return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "백엔드 내부 오류")

    return ApiResponse(status.HTTP_200_OK, None)
