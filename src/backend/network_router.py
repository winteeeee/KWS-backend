from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.factories import MySQLEngineFactory
from model.api_models import ApiResponse, NetworkResponseDTO
from openStack.openstack_controller import OpenStackController
from util.logger import get_logger
from model.db_models import Network

network_router = APIRouter(prefix="/network")
controller = OpenStackController()
db_connection = MySQLEngineFactory().get_instance()
backend_logger = get_logger(name='backend', log_level='INFO', save_path="./log/backend")


@network_router.get("/list")
def networks():
    result = []
    backend_logger.info("네트워크 조회")

    with Session(db_connection) as session, session.begin():
        networks = session.scalars(select(Network)).all()
        for network in networks:
            result.append(NetworkResponseDTO(name=network.name,
                                             subnet_cidr=network.cidr).__dict__)

    return ApiResponse(status.HTTP_200_OK, result)
