from sqlalchemy import select
from sqlalchemy.orm import Session

from database.factories import MySQLEngineFactory
from model.db_models import Node, Server, Flavor
from openStack.openstack_controller import OpenStackController
from util.logger import get_logger
from config.config import node_config

controller = OpenStackController()
db_connection = MySQLEngineFactory().get_instance()
backend_logger = get_logger(name='backend', log_level='INFO', save_path="./log/backend")
node_idx = 0


def get_remaining_resources():
    with Session(db_connection) as session, session.begin():
        remaining_resources_by_node = []

        for node in node_config['nodes']:
            current_node = session.scalars(select(Node).where(Node.name == node['name'])).one()
            servers = session.scalars(select(Server).where(Server.node_name == node['name']))

            using_vcpus = 0
            using_ram = 0
            using_disk = 0

            for server in servers:
                flavor = session.scalars(select(Flavor).where(Flavor.name == server.flavor_name)).one()
                using_vcpus += flavor.vcpu
                using_ram += flavor.ram
                using_disk += flavor.disk

            remaining_vcpu = current_node.vcpu - using_vcpus
            remaining_ram = current_node.ram - int(using_ram / 1024)
            remaining_disk = current_node.disk - using_disk

            remaining_resources_by_node.append({
                'name': node['name'],
                'vcpu': remaining_vcpu,
                'ram': remaining_ram,
                'disk': remaining_disk
            })

        return remaining_resources_by_node


def get_available_node(vcpu: int, ram: int, disk: int):
    nodes = get_remaining_resources()

    for node in nodes:
        backend_logger.info(f"[{node['name']}] : 리소스 탐색 중")
        if vcpu <= node["vcpu"] and int(ram / 1024) <= node["ram"] and disk <= node["disk"]:
            return node["name"]

    return None


def get_available_container_node():
    global node_idx

    nodes = node_config['nodes']
    node_name = nodes[node_idx]['name']
    node_idx = (node_idx + 1) % len(nodes)
    return node_name
