import io
from datetime import date
from fastapi import APIRouter, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.factories import MySQLEngineFactory
from model.db_models import Server, Flavor, NodeFlavor, Network, NodeNetwork
from model.api_request_models import ServerCreateRequestDTO
from model.api_response_models import ApiResponse, ServerRentalResponseDTO, ErrorResponse, ServersResponseDTO
from openStack.openstack_controller import OpenStackController
from util.utils import validate_ssh_key
from util.backend_utils import network_isolation, network_delete
from util.logger import get_logger
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
        if server_info.network_name is None:
            backend_logger.info("기본 내부 네트워크 사용")
            server_info.network_name = openstack_config['internal_network']['name']
        
        backend_logger.info("서버 이름 중복 여부 검사")
        if session.scalars(select(Server).where(Server.server_name == server_info.server_name)).one_or_none() is not None:
            return ErrorResponse(status.HTTP_400_BAD_REQUEST, "서버 이름 중복")


        try:
            backend_logger.info("커스텀 플레이버 생성 여부 검사")
            if session.scalars(select(Flavor).where(Flavor.name == server_info.flavor_name)).one_or_none() is None:
                backend_logger.info("시스템에 해당 플레이버 존재하지 않음")
                backend_logger.info("데이터베이스에 플레이버 삽입")
                session.add(Flavor(
                    name=server_info.flavor_name,
                    vcpu=server_info.vcpus,
                    ram=server_info.ram,
                    disk=server_info.disk,
                    is_default=False
                ))

            if session.scalars(select(NodeFlavor).where(NodeFlavor.flavor_name == server_info.flavor_name,
                                                        NodeFlavor.node_name == server_info.node_name)).one_or_none() is None:
                backend_logger.info("커스텀 플레이버 생성 시작")
                backend_logger.info(f"[{server_info.node_name}] : 커스텀 플레이버 생성 시작")
                controller.create_flavor(flavor_name=server_info.flavor_name,
                                         node_name=server_info.node_name,
                                         vcpus=server_info.vcpus,
                                         ram=server_info.ram,
                                         disk=server_info.disk)
        except Exception as e:
            backend_logger.error(e)
            session.rollback()
            controller.delete_flavor(flavor_name=server_info.flavor_name,
                                     node_name=server_info.node_name)
            return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "커스텀 플레이버 생성 오류")

        # 네트워크 분리 적용
        backend_logger.info("네트워크 분리 여부 검사")
        try:
            # 해당 네트워크가 없다면
            if session.scalars(select(Network).where(Network.name == server_info.network_name)).one_or_none() is None:
                backend_logger.info("시스템에 해당 네트워크 존재하지 않음")
                backend_logger.info("데이터베이스에 네트워크 삽입")
                session.add(Network(
                    name=server_info.network_name,
                    cidr=server_info.subnet_cidr,
                    is_default=False,
                    is_external=False,
                ))
    
            # 해당 노드의 네트워크가 없다면
            if session.scalars(select(NodeNetwork).where(NodeNetwork.network_name == server_info.network_name and
                                                         NodeNetwork.node_name == server_info.node_name)).one_or_none() is None:
                network_isolation(controller=controller,
                                  node_name=server_info.node_name,
                                  backend_logger=backend_logger,
                                  network_name=server_info.network_name,
                                  subnet_cidr=server_info.subnet_cidr)
    
                session.add(NodeNetwork(node_name=server_info.node_name,
                                        network_name=server_info.network_name))
        except Exception as e:
            backend_logger.error(e)
            # 네트워크 분리 복구
            node_network = session.scalars(select(NodeNetwork).where(NodeNetwork.network_name == server_info.network_name,
                                                         NodeNetwork.node_name == server_info.node_name)).one_or_none()
            if node_network is not None and not node_network.network.is_default:
                network_delete(controller=controller,
                               node_name=server_info.node_name,
                               network_name=server_info.network_name,
                               backend_logger=backend_logger)
            session.rollback()
            return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "네트워크 분리 오류")

        try:
            backend_logger.info("서버 생성")
            server, private_key = controller.create_server(server_name=server_info.server_name,
                                                           image_name=server_info.image_name,
                                                           flavor_name=server_info.flavor_name,
                                                           network_name=server_info.network_name,
                                                           password=server_info.password,
                                                           cloud_init=server_info.cloud_init,
                                                           node_name=server_info.node_name)
            backend_logger.info("유동 IP 할당")
            floating_ip = controller.allocate_floating_ip(server=server, node_name=server_info.node_name)

            server = Server(
                user_name=server_info.user_name,
                server_name=server_info.server_name,
                start_date=server_info.start_date,
                end_date=server_info.end_date,
                floating_ip=floating_ip,
                network_name=server_info.network_name,
                node_name=server_info.node_name,
                flavor_name=server_info.flavor_name,
                image_name=server_info.image_name
            )
            backend_logger.info("데이터베이스에 인스턴스 저장")
            session.add(server)
            session.commit()
        except Exception as e:
            backend_logger.error(e)
            session.rollback()
            controller.delete_server(server_name=server_info.server_name,
                                     node_name=server_info.node_name,
                                     server_ip=floating_ip)
            return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "백엔드 내부 오류")
        
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
                split_date = end_date.split(sep='-')
                server.end_date = date(int(split_date[0]), int(split_date[1]), int(split_date[2]))
                session.add(server)
                session.commit()
            except Exception as e:
                backend_logger.error(e)
                session.rollback()
                return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "백엔드 내부 오류")
        return ApiResponse(status.HTTP_200_OK, None)
    else:
        return ErrorResponse(status.HTTP_400_BAD_REQUEST, "입력한 정보가 잘못됨")


@server_router.delete("/return")
async def server_return(server_name: str = Form(...),
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
                backend_logger.info("서버 삭제")
                controller.delete_server(server_name=server_name, node_name=server.node_name, server_ip=host_ip)
                backend_logger.info("데이터베이스에 서버 삭제")
                session.delete(server)
                session.commit()

                # 커스텀 플레이버 삭제
                flavor = session.scalars(select(Flavor).where(Flavor.name == flavor_name)).one()
                if len(flavor.servers) == 0 and not flavor.is_default:
                    backend_logger.info("커스텀 플레이버를 사용 중인 서버 없음")
                    backend_logger.info("커스텀 플레이버 삭제")

                    backend_logger.info("데이터베이스에 플레이버 삭제")
                    target_node_flavors = session.scalars(select(NodeFlavor)
                                                          .where(NodeFlavor.flavor_name == flavor_name)).all()
                    # 외래키 제약 조건이 있으니 중간 테이블부터 삭제
                    for target_node_flavor in target_node_flavors:
                        controller.delete_flavor(flavor_name=target_node_flavor.flavor_name,
                                                 node_name=target_node_flavor.node_name)
                        session.delete(target_node_flavor)
                    session.delete(flavor)

                # 내부 네트워크 삭제
                network = session.scalars(select(Network).where(Network.name == network_name)).one()
                attached_servers_on_network = len(network.servers)
                attached_containers_on_network = len(network.containers)
                if attached_servers_on_network + attached_containers_on_network == 0 and not network.is_default:
                    backend_logger.info("내부 네트워크를 사용 중인 서버/컨테이너 없음")
                    backend_logger.info("내부 네트워크 삭제 시작")

                    backend_logger.info("데이터베이스에 네트워크 삭제")
                    target_node_networks = session.scalars(
                        select(NodeNetwork).where(NodeNetwork.network_name == network_name)).all()
                    # 외래키 제약 조건이 있으니 중간 테이블부터 삭제
                    for target_node_network in target_node_networks:
                        network_delete(controller=controller,
                                       node_name=target_node_network.node_name,
                                       backend_logger=backend_logger,
                                       network_name=target_node_network.network_name)
                        session.delete(target_node_network)
                    session.delete(network)
                session.commit()
            except Exception as e:
                backend_logger.error(e)
                return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "백엔드 내부 오류")

        return ApiResponse(status.HTTP_200_OK, None)
    else:
        return ErrorResponse(status.HTTP_400_BAD_REQUEST, "입력한 정보가 잘못됨")
