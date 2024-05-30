import io
from fastapi import APIRouter, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.factories import MySQLEngineFactory
from model.db_models import Server, Flavor, NodeFlavor
from model.api_request_models import ServerCreateRequestDTO
from model.api_response_models import ApiResponse, ServerRentalResponseDTO, ErrorResponse, ServersResponseDTO
from openStack.openstack_controller import OpenStackController
from util.utils import validate_ssh_key, alphabet_check, str_to_date, extension_date_check
from util.backend_utils import create_network, network_delete, network_rollback, flavor_delete
from util.logger import get_logger
from util.selector import get_available_node
from config.config import openstack_config

server_router = APIRouter(prefix="/server")
controller = OpenStackController()
db_connection = MySQLEngineFactory().get_instance()
backend_logger = get_logger(name='backend', log_level='INFO', save_path="./log/backend")


@server_router.get("/list")
def server_show():
    with Session(db_connection) as session, session.begin():
        backend_logger.info("서버 목록 요청 수신")
        servers = session.scalars(select(Server)).all()
        server_list = []
        for server in servers:
            server_dict = server.__dict__
            del server_dict['id']
            del server_dict['_sa_instance_state']
            server_list.append(ServersResponseDTO(**server_dict).__dict__)
    return ApiResponse(status.HTTP_200_OK, server_list)


@server_router.post("/rental")
def server_rent(server_info: ServerCreateRequestDTO):
    backend_logger.info("서버 대여 요청 수신")
    with Session(db_connection) as session:
        backend_logger.info("서버 이름 중복 여부 검사")
        if len(session.scalars(select(Server).where(Server.server_name == server_info.server_name)).all()) != 0:
            return ErrorResponse(status.HTTP_400_BAD_REQUEST, "서버 이름 중복")

        backend_logger.info("서버 이름 검사")
        if not alphabet_check(server_info.server_name):
            return ErrorResponse(status.HTTP_400_BAD_REQUEST, "서버 이름은 알파벳과 숫자로만 구성되어야 합니다.")

        if server_info.network_name is None:
            backend_logger.info("기본 내부 네트워크 사용")
            server_info.network_name = openstack_config['internal_network']['name']

        backend_logger.info("노드 선택")
        node_name = get_available_node(server_info.vcpus, server_info.ram, server_info.disk)
        if node_name is None:
            return ErrorResponse(status.HTTP_406_NOT_ACCEPTABLE, "시스템의 리소스가 부족합니다.")

        try:
            backend_logger.info("커스텀 플레이버 생성 여부 검사")
            if len(session.scalars(select(Flavor).where(Flavor.name == server_info.flavor_name)).all()) == 0:
                backend_logger.info("시스템에 해당 플레이버 존재하지 않음")
                backend_logger.info("데이터베이스에 플레이버 삽입")
                session.add(Flavor(
                    name=server_info.flavor_name,
                    vcpu=server_info.vcpus,
                    ram=server_info.ram,
                    disk=server_info.disk,
                    is_default=False
                ))

            if len(session.scalars(select(NodeFlavor).where(NodeFlavor.flavor_name == server_info.flavor_name,
                                                            NodeFlavor.node_name == node_name)).all()) == 0:
                backend_logger.info("커스텀 플레이버 생성 시작")
                backend_logger.info(f"[{node_name}] : 커스텀 플레이버 생성 시작")
                controller.create_flavor(flavor_name=server_info.flavor_name,
                                         node_name=node_name,
                                         vcpus=server_info.vcpus,
                                         ram=server_info.ram,
                                         disk=server_info.disk)

            create_network(session=session,
                           controller=controller,
                           network_name=server_info.network_name,
                           subnet_cidr=server_info.subnet_cidr,
                           node_name=node_name)

            backend_logger.info("서버 생성")
            floating_ip = None
            server, private_key = controller.create_server(server_name=server_info.server_name,
                                                           image_name=server_info.image_name,
                                                           flavor_name=server_info.flavor_name,
                                                           network_name=server_info.network_name,
                                                           password=server_info.password,
                                                           cloud_init=server_info.cloud_init,
                                                           node_name=node_name)
            backend_logger.info("유동 IP 할당")
            floating_ip = controller.allocate_floating_ip(server=server, node_name=node_name)

            server = Server(
                user_name=server_info.user_name,
                server_name=server_info.server_name,
                start_date=server_info.start_date,
                end_date=server_info.end_date,
                floating_ip=floating_ip,
                network_name=server_info.network_name,
                node_name=node_name,
                flavor_name=server_info.flavor_name,
                image_name=server_info.image_name
            )
            backend_logger.info("데이터베이스에 인스턴스 저장")
            session.add(server)
            session.commit()
        except Exception as e:
            backend_logger.error(e)
            flavor = session.scalars(select(Flavor).where(Flavor.name == server_info.flavor_name)).one()
            if not flavor.is_default:
                controller.delete_flavor(flavor_name=server_info.flavor_name,
                                         node_name=node_name)
            network_rollback(session=session,
                             controller=controller,
                             network_name=server_info.network_name,
                             node_name=node_name)
            controller.delete_server(server_name=server_info.server_name,
                                     node_name=node_name,
                                     server_ip=floating_ip)
            session.rollback()
            return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
        
    name = f'{server_info.server_name}_keypair.pem' if private_key != "" else ""
    return ApiResponse(status.HTTP_201_CREATED, ServerRentalResponseDTO(name, private_key).__dict__)


@server_router.put("/extension")
def server_renew(server_name: str = Form(...),
                 host_ip: str = Form(...),
                 end_date: str = Form(...),
                 password: str = Form(""),
                 key_file: UploadFile = Form("")):
    backend_logger.info("서버 연장 요청 수신")
    key_file = io.StringIO(key_file.file.read().decode('utf-8')) \
        if key_file != "" else key_file

    backend_logger.info("정보 유효성 검사 중")
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

                new_end_date = str_to_date(end_date)
                if not extension_date_check(old_end_date=server.end_date, new_end_date=new_end_date):
                    return ErrorResponse(status.HTTP_400_BAD_REQUEST, "현재 대여 종료 일자 이후의 날짜를 선택 해야 합니다.")

                server.end_date = new_end_date
                session.add(server)
                session.commit()
            except Exception as e:
                backend_logger.error(e)
                session.rollback()
                return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))
        return ApiResponse(status.HTTP_200_OK, None)
    else:
        return ErrorResponse(status.HTTP_400_BAD_REQUEST, "입력한 정보가 잘못됨")


@server_router.delete("/return")
def server_return(server_name: str = Form(...),
                  host_ip: str = Form(...),
                  password: str = Form(""),
                  key_file: UploadFile = Form("")):
    backend_logger.info("서버 반환 요청 수신")
    key_file = io.StringIO(key_file.file.read().decode('utf-8')) \
        if key_file != "" else key_file

    backend_logger.info("정보 유효성 검사 중")
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
                network_name = server.network_name
                flavor_name = server.flavor_name
                node_name = server.node_name

                backend_logger.info("서버 삭제")
                controller.delete_server(server_name=server_name, node_name=server.node_name, server_ip=host_ip)
                backend_logger.info("데이터베이스에 서버 삭제")
                session.delete(server)
                session.commit()

                flavor_delete(session=session,
                              controller=controller,
                              flavor_name=flavor_name,
                              node_name=node_name)
                network_delete(session=session,
                               controller=controller,
                               network_name=network_name,
                               node_name=node_name)
                session.commit()
            except Exception as e:
                backend_logger.error(e)
                return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))

        return ApiResponse(status.HTTP_200_OK, None)
    else:
        return ErrorResponse(status.HTTP_400_BAD_REQUEST, "입력한 정보가 잘못됨")
