from fastapi import APIRouter, status

from database.factories import MySQLEngineFactory
from model.api_response_models import ApiResponse, ImageListResponseDTO, ErrorResponse
from openStack.openstack_controller import OpenStackController
from util.logger import get_logger
from config.config import node_config

image_router = APIRouter(prefix="/image")
controller = OpenStackController()
db_connection = MySQLEngineFactory().get_instance()
backend_logger = get_logger(name='backend', log_level='INFO', save_path="./log/backend")


@image_router.get("/list")
def image_list_show():
    try:
        backend_logger.info("이미지 조회 요청 수신")
        # 이미지는 노드 별로 달라질 수 없으므로 0번째 노드만 탐색
        images = controller.find_images(node_name=node_config['nodes'][0]['name'])
    except Exception as e:
        backend_logger.error(e)
        return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "백엔드 내부 오류")

    image_list = [ImageListResponseDTO(image.name).__dict__ for image in images]
    return ApiResponse(status.HTTP_200_OK, image_list)
