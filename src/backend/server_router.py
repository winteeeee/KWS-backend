import io
from datetime import date
from fastapi import APIRouter, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.factories import MySQLEngineFactory
from model.db_models import Server, Node, Container
from model.api_models import (ApiResponse, ServerCreateRequestDTO, ServerRentalResponseDTO, ImageListResponseDTO,
                              FlavorListResponseDTO, UsingResourceDTO, UsingResourcesResponseDTO, NodeUsingResourceDTO,
                              ErrorResponse, NetworkResponseDTO, NodeSpecDTO, NodesSpecResponseDTO, ResourceResponseDTO,
                              ServersResponseDTO)
from openStack.openstack_controller import OpenStackController
from util.utils import validate_ssh_key, generator_len
from util.backend_utils import network_isolation, network_delete
from util.logger import get_logger
from config.config import openstack_config, node_config

server_router = APIRouter(prefix="/server")
controller = OpenStackController()
db_connection = MySQLEngineFactory().get_instance()
backend_logger = get_logger(name='backend', log_level='INFO', save_path="./log/backend")


@server_router.get("/list")
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


@server_router.post("/rental")
def server_rent(server_info: ServerCreateRequestDTO):
    backend_logger.info("서버 이름 중복 체크")
    if controller.find_server(server_name=server_info.server_name,
                              node_name=server_info.node_name) is not None:
        return ErrorResponse(status.HTTP_400_BAD_REQUEST, "서버 이름 중복")

    with Session(db_connection) as session:
        session.begin()
        if server_info.network_name is None:
            server_info.network_name = openstack_config['default_internal_network']

        try:
            backend_logger.info("커스텀 플레이버 생성 여부 검사")
            if controller.find_flavor(flavor_name=server_info.flavor_name,
                                      node_name=server_info.node_name) is None:
                backend_logger.info("커스텀 플레이버 생성 시작")
                for node in node_config['nodes']:
                    backend_logger.info(f"[{node['name']}] : 커스텀 플레이버 생성 시작")
                    controller.create_flavor(flavor_name=server_info.flavor_name,
                                             node_name=node['name'],
                                             vcpus=server_info.vcpus,
                                             ram=server_info.ram,
                                             disk=server_info.disk)
        except Exception as e:
            backend_logger.error(e)
            return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "커스텀 플레이버 생성 오류")

        # 네트워크 분리 적용
        backend_logger.info("네트워크 분리 여부 검사")
        if controller.find_network(network_name=server_info.network_name,
                                   node_name=server_info.node_name,
                                   logger_on=False) is None:
            for node in node_config['nodes']:
                network_isolation(controller=controller,
                                  node_name=node['name'],
                                  backend_logger=backend_logger,
                                  network_name=server_info.network_name,
                                  subnet_cidr=server_info.subnet_cidr)

        try:
            backend_logger.info("서버 생성")
            server, private_key = controller.create_server(server_info=server_info,
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
            if server_info.flavor_name not in openstack_config['default_flavors']:
                for node in node_config['nodes']:
                    backend_logger.info(f"[{node['name']}] : 커스텀 플레이버 삭제 시작")
                    controller.delete_flavor(flavor_name=server_info.flavor_name,
                                             node_name=node['name'])
            return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "백엔드 내부 오류")
        
    name = f'{server_info.server_name}_keypair.pem' if private_key != "" else ""
    return ApiResponse(status.HTTP_201_CREATED, ServerRentalResponseDTO(name, private_key).__dict__)


@server_router.put("/extension")
def server_renew(server_name: str = Form(...),
                 host_ip: str = Form(...),
                 end_date: str = Form(...),
                 password: str = Form(""),
                 key_file: UploadFile = Form("")):
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
        return ApiResponse(status.HTTP_200_OK, "대여 기간 연장 완료")
    else:
        return ErrorResponse(status.HTTP_400_BAD_REQUEST, "입력한 정보가 잘못됨")


@server_router.delete("/return")
async def server_return(server_name: str = Form(...),
                        host_ip: str = Form(...),
                        password: str = Form(""),
                        key_file: UploadFile = Form("")):
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
                backend_logger.info("데이터베이스에 서버 삭제")
                session.delete(server)
                session.commit()
                backend_logger.info("시스템에서 서버 삭제")
                controller.delete_server(server_name=server_name, node_name=server.node_name, server_ip=host_ip)

                openstack_server = controller.find_server(server_name=server_name, node_name=server.node_name)
                # 기본 제공 플레이버가 아니면 삭제
                if openstack_server.flavor.original_name not in openstack_config['default_flavors']:
                    if session.scalars(select(Server).where(Server.flavor_name == openstack_server.flavor.original_name)).one_or_none() is None:
                        backend_logger.info("사용 중인 커스텀 플레이버 없음")
                        backend_logger.info("커스텀 플레이버 삭제 시작")
                        for node in node_config['nodes']:
                            backend_logger.info(f"[{node['name']}] : 커스텀 플레이버 삭제 시작")
                            controller.delete_flavor(flavor_name=openstack_server.flavor.original_name,
                                                     node_name=node['name'])

                if (network_name != openstack_config['external_network'] and
                    network_name != openstack_config['default_internal_network'] and
                    session.scalars(select(Server).where(Server.network_name == network_name)).one_or_none() is None and
                        session.scalars(select(Container).where(Container.network_name == network_name)).one_or_none() is None):
                    backend_logger.info("사용 중인 내부 네트워크 없음")
                    backend_logger.info("내부 네트워크 삭제 시작")
                    for node in node_config['nodes']:
                        network_delete(controller=controller,
                                       node_name=node['name'],
                                       backend_logger=backend_logger,
                                       network_name=network_name)
            except Exception as e:
                backend_logger.error(e)
                return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "백엔드 내부 오류")

        return ApiResponse(status.HTTP_200_OK, "서버 삭제 완료")
    else:
        return ErrorResponse(status.HTTP_400_BAD_REQUEST, "입력한 정보가 잘못됨")


@server_router.get("/resources")
def get_resources():
    with Session(db_connection) as session, session.begin():
        limit_total_resource = {}
        using_total_resource = {}
        limit_resource_by_node = []
        using_resource_by_node = []
        total_limit_vcpu = 0
        total_limit_ram = 0
        total_limit_disk = 0
        total_using_vcpu = 0
        total_using_ram = 0
        total_using_disk = 0
        total_server_count = 0

        for node in node_config['nodes']:
            backend_logger.info(f"[{node['name']}] : 리소스 탐색 중")
            compute_node = session.scalars(select(Node).where(Node.name == node['name'])).one()
            servers = session.scalars(select(Server).where(Server.node_name == node['name']))

            server_count = 0
            using_vcpus = 0
            using_ram = 0
            using_disk = 0
            total_limit_vcpu += compute_node.vcpu
            total_limit_ram += compute_node.ram
            total_limit_disk += compute_node.disk

            for server in servers:
                server_count += 1
                flavor = controller.find_flavor(flavor_name=server.flavor_name, node_name=node['name'])
                total_using_vcpu += flavor.vcpus
                total_using_ram += flavor.ram
                total_using_disk += flavor.disk
                using_vcpus += flavor.vcpus
                using_ram += flavor.ram
                using_disk += flavor.disk

            total_server_count += server_count
            using_resource_by_node.append(NodeUsingResourceDTO(name=node['name'],
                                                               count=server_count,
                                                               vcpus=using_vcpus,
                                                               ram=float(using_ram / 1024),
                                                               disk=using_disk).__dict__)
            compute_node_dict = compute_node.__dict__
            del compute_node_dict['id']
            del compute_node_dict['_sa_instance_state']
            del compute_node_dict['auth_url']
            limit_resource_by_node.append(NodeSpecDTO(**compute_node_dict).__dict__)

        limit_total_resource = {'vcpu': total_limit_vcpu, 'ram': total_limit_ram, 'disk': total_limit_disk}
        using_total_resource = UsingResourceDTO(count=total_server_count,
                                                vcpus=total_using_vcpu,
                                                ram=total_using_ram,
                                                disk=total_using_disk).__dict__
        limit_resources = NodesSpecResponseDTO(total_spec=limit_total_resource,
                                               nodes_spec=limit_resource_by_node).__dict__
        using_resources = UsingResourcesResponseDTO(total_resource=using_total_resource,
                                                    nodes_resource=using_resource_by_node).__dict__
    return ApiResponse(status.HTTP_200_OK, ResourceResponseDTO(limit_resources=limit_resources,
                                                               using_resources=using_resources).__dict__)
