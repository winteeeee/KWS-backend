from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.factories import MySQLEngineFactory
from model.api_response_models import (ApiResponse, UsingResourceDTO, UsingResourcesResponseDTO, NodeUsingResourceDTO,
                                       NodeSpecDTO, NodesSpecResponseDTO, ResourceResponseDTO, NodeResponseDTO)
from model.db_models import Node, Server
from openStack.openstack_controller import OpenStackController
from util.logger import get_logger
from config.config import node_config

node_router = APIRouter(prefix="/node")
controller = OpenStackController()
db_connection = MySQLEngineFactory().get_instance()
backend_logger = get_logger(name='backend', log_level='INFO', save_path="./log/backend")


@node_router.get("/list")
def node_list_show():
    node_list = []
    backend_logger.info("노드 목록 요청 수신")

    with Session(db_connection) as session, session.begin():
        nodes = session.scalars(select(Node)).all()
        for node in nodes:
            node_list.append(NodeResponseDTO(name=node.name,
                                             vcpu=node.vcpu,
                                             ram=node.ram,
                                             disk=node.disk).__dict__)
    return ApiResponse(status.HTTP_200_OK, node_list)


@node_router.get("/resources")
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
