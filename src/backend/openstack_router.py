import io
from fastapi import APIRouter, Form, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.factories import MySQLEngineFactory
from model.db_models import Server, Node
from model.api_models import (ApiResponse, ServerCreateRequestDTO, ServerRentalResponseDTO, ImageListResponseDTO,
                              FlavorListResponseDTO, UsingResourceDTO, UsingResourcesResponseDTO, NodeUsingResourceDTO, ErrorResponse,
                              NetworkResponseDTO, NodeSpecDTO, NodesSpecResponseDTO, ResourceResponseDTO)
from openStack.openstack_controller import OpenStackController
from util.utils import validate_ssh_key, gateway_extractor, generator_len
from config.config import openstack_config, node_config

openstack_router = APIRouter(prefix="/openstack")
controller = OpenStackController()
db_connection = MySQLEngineFactory().get_instance()


@openstack_router.post("/rental")
def server_rent(server_info: ServerCreateRequestDTO):
    if controller.find_server(server_info.server_name) is not None:
        return ErrorResponse(status.HTTP_400_BAD_REQUEST, "서버 이름 중복")

    with Session(db_connection) as session:
        session.begin()
        try:
            # 커스텀 플레이버 적용
            if controller.find_flavor(server_info.flavor_name) is None:
                controller.create_flavor(flavor_name=server_info.flavor_name,
                                         vcpus=server_info.vcpus,
                                         ram=server_info.ram,
                                         disk=server_info.disk)
        except:
            return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "플레이버 생성 오류")

        # 네트워크 분리 적용
        if controller.find_network(server_info.network_name) is None:
            subnet_name = f'{server_info.network_name}_subnet'
            router_name = f'{server_info.network_name}_router'

            try:
                controller.create_network(network_name=server_info.network_name, external=False)
            except:
                return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "네트워크 생성 오류")

            try:
                controller.create_subnet(subnet_name=subnet_name,
                                         ip_version=4,
                                         subnet_address=server_info.subnet_cidr,
                                         subnet_gateway=gateway_extractor(server_info.subnet_cidr),
                                         network_name=server_info.network_name)
            except:
                controller.delete_network(network_name=server_info.network_name)
                return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "서브넷 생성 오류")

            try:
                controller.create_router(router_name=router_name,
                                         external_network_name=openstack_config['external_network'],
                                         external_subnet_name=openstack_config['external_network_subnet'])
            except:
                controller.delete_network(network_name=server_info.network_name)
                controller.delete_subnet(subnet_name=subnet_name)
                return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "라우터 생성 오류")

            try:
                controller.add_interface_to_router(router_name=router_name,
                                                   internal_subnet_name=subnet_name)
            except:
                controller.delete_network(network_name=server_info.network_name)
                controller.delete_subnet(subnet_name=subnet_name)
                controller.delete_router(router_name=router_name)
                return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "인터페이스 추가 오류")

        try:
            server, private_key = controller.create_server(server_info)
            floating_ip = controller.allocate_floating_ip(server)

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
            session.add(server)
            session.commit()
        except:
            session.rollback()
            controller.delete_server(server_info.server_name, floating_ip)
            return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "백엔드 내부 오류")
        
    name = f'{server_info.server_name}_keypair.pem' if private_key != "" else ""
    return ApiResponse(status.HTTP_201_CREATED, ServerRentalResponseDTO(name, private_key).__dict__)


@openstack_router.get("/image_list")
def image_list_show():
    try:
        images = controller.find_images()
    except:
        return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "백엔드 내부 오류")

    image_list = [ImageListResponseDTO(image.name).__dict__ for image in images]
    return ApiResponse(status.HTTP_200_OK, image_list)


@openstack_router.get("/flavor_list")
def flavor_list_show():
    try:
        flavors = controller.find_flavors()
    except:
        return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "백엔드 내부 오류")

    flavor_list = []
    for flavor in flavors:
        if flavor.name in openstack_config['default_flavors']:
            flavor_list.append(FlavorListResponseDTO(flavor.name, flavor.vcpus, flavor.ram, flavor.disk))
    flavor_list = sorted(flavor_list, key=lambda f: (f.cpu, f.ram, f.disk))
    return ApiResponse(status.HTTP_200_OK, [f.__dict__ for f in flavor_list])


@openstack_router.delete("/return")
async def server_return(server_name: str = Form(...),
                        host_ip: str = Form(...),
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
                session.delete(server)
                controller.delete_server(server_name, host_ip)

                openstack_server = controller.find_server(server_name)
                # 기본 제공 플레이버가 아니면 삭제
                if openstack_server.flavor.original_name not in openstack_config['default_flavors']:
                    controller.delete_flavor(openstack_server.flavor.original_name)

                # 기본 제공 네트워크가 아니면서 이것 외에 할당된 다른 VM이 없으면 네트워크, 라우터, 서브넷 삭제
                network_name = ''
                for n in openstack_server.addresses.keys():
                    network_name = n
                if network_name != openstack_config['default_internal_network'] and network_name != openstack_config['external_network']:
                    if generator_len(controller.find_ports(network_id=controller.find_network(network_name).id)) <= 3:
                        subnet_name = f'{network_name}_subnet'
                        router_name = f'{network_name}_router'

                        controller.remove_interface_from_router(router_name=router_name,
                                                                internal_subnet_name=subnet_name)
                        controller.delete_router(router_name=router_name)
                        controller.delete_network(network_name=network_name)
                session.commit()
            except:
                return ErrorResponse(status.HTTP_500_INTERNAL_SERVER_ERROR, "백엔드 내부 오류")

        return ApiResponse(status.HTTP_200_OK, "서버 삭제 완료")
    else:
        return ErrorResponse(status.HTTP_400_BAD_REQUEST, "입력한 정보가 잘못됨")


@openstack_router.get("/resources")
def get_resources():
    with Session(db_connection) as session, session.begin():
        limit_total_resource = {}
        using_total_resource = UsingResourceDTO(**controller.monitoring_resources()).__dict__
        limit_resource_by_node = []
        using_resource_by_node = []
        total_limit_vcpu = 0
        total_limit_ram = 0
        total_limit_disk = 0

        for node in node_config['compute']:
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
                flavor = controller.find_flavor(flavor_name=server.flavor_name)
                using_vcpus += flavor.vcpus
                using_ram += flavor.ram
                using_disk += flavor.disk

            using_resource_by_node.append(NodeUsingResourceDTO(name=node['name'],
                                                               count=server_count,
                                                               vcpus=using_vcpus,
                                                               ram=float(using_ram / 1024),
                                                               disk=using_disk).__dict__)
            compute_node_dict = compute_node.__dict__
            del compute_node_dict['id']
            del compute_node_dict['_sa_instance_state']
            limit_resource_by_node.append(NodeSpecDTO(**compute_node_dict).__dict__)

        limit_total_resource = {'vcpu': total_limit_vcpu, 'ram': total_limit_ram, 'disk': total_limit_disk}
        limit_resources = NodesSpecResponseDTO(total_spec=limit_total_resource,
                                               nodes_spec=limit_resource_by_node).__dict__
        using_resources = UsingResourcesResponseDTO(total_resource=using_total_resource,
                                                    nodes_resource=using_resource_by_node).__dict__
    return ApiResponse(status.HTTP_200_OK, ResourceResponseDTO(limit_resources=limit_resources,
                                                               using_resources=using_resources).__dict__)


@openstack_router.get("/networks")
def networks():
    result = []

    openstack_networks = controller.find_networks()
    for network in openstack_networks:
        if not network.is_router_external:
            result.append(NetworkResponseDTO(name=network.name,
                                             subnet_cidr=controller.find_subnet(network.subnet_ids[0]).cidr).__dict__)

    return ApiResponse(status.HTTP_200_OK, result)
