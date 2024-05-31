from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.factories import MySQLEngineFactory
from model.api_response_models import ApiResponse, FlavorListResponseDTO
from openStack.openstack_controller import OpenStackController
from util.logger import get_logger
from model.db_models import Flavor

flavor_router = APIRouter(prefix="/flavor")
controller = OpenStackController()
db_connection = MySQLEngineFactory().get_instance()
backend_logger = get_logger(name='backend', log_level='INFO', save_path="./log/backend")


@flavor_router.get("/list")
def flavor_list_show():
    flavor_list = []
    backend_logger.info("플레이버 조회 요청 수신")

    with Session(db_connection) as session, session.begin():
        flavors = session.scalars(select(Flavor)).all()
        for flavor in flavors:
            flavor_list.append(FlavorListResponseDTO(flavor.name, flavor.vcpu, flavor.ram, flavor.disk))
    flavor_list = sorted(flavor_list, key=lambda f: (f.cpu, f.ram, f.disk))
    return ApiResponse(status.HTTP_200_OK, [f.__dict__ for f in flavor_list])
