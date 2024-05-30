import sqlalchemy.orm

import openStack.openstack_controller
from util.utils import gateway_extractor, subnet_name_creator
from config.config import openstack_config
from util.logger import get_logger
from sqlalchemy import select
from model.db_models import Network, NodeNetwork, Flavor, NodeFlavor


backend_logger = get_logger(name='backend', log_level='INFO', save_path="./log/backend")


def _network_isolation(controller: openStack.openstack_controller.OpenStackController,
                       node_name,
                       network_name,
                       subnet_cidr):
    backend_logger.info(f"[{node_name}]: 네트워크 분리 중")
    subnet_name = f'{network_name}_subnet'

    controller.create_network(network_name=network_name, node_name=node_name, external=False)
    controller.create_subnet(subnet_name=subnet_name,
                             node_name=node_name,
                             ip_version=4,
                             subnet_address=subnet_cidr,
                             subnet_gateway=gateway_extractor(subnet_cidr),
                             network_name=network_name)
    controller.add_interface_to_router(router_name=openstack_config['router'],
                                       node_name=node_name,
                                       internal_subnet_name=subnet_name)


def create_network(session: sqlalchemy.orm.Session,
                   controller: openStack.openstack_controller.OpenStackController,
                   network_name: str,
                   subnet_cidr: str,
                   node_name: str):
    backend_logger.info("네트워크 분리 여부 검사")
    if len(session.scalars(select(Network).where(Network.name == network_name)).all()) == 0:
        backend_logger.info("시스템에 해당 네트워크 존재하지 않음")
        backend_logger.info("데이터베이스에 네트워크 삽입")
        session.add(Network(
            name=network_name,
            cidr=subnet_cidr,
            is_default=False,
            is_external=False,
        ))

    # 해당 노드의 네트워크가 없다면
    if len(session.scalars(select(NodeNetwork).where(NodeNetwork.network_name == network_name,
                                                     NodeNetwork.node_name == node_name)).all()) == 0:
        _network_isolation(controller=controller,
                           node_name=node_name,
                           network_name=network_name,
                           subnet_cidr=subnet_cidr)

        session.add(NodeNetwork(node_name=node_name,
                                network_name=network_name))


def network_delete(session: sqlalchemy.orm.Session,
                   controller: openStack.openstack_controller.OpenStackController,
                   network_name: str,
                   node_name: str):
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
            controller.remove_interface_from_router(router_name=openstack_config['router'],
                                                    node_name=node_name,
                                                    internal_subnet_name=subnet_name_creator(network_name))
            controller.delete_network(network_name=network_name, node_name=node_name)
            session.delete(target_node_network)
        session.delete(network)


def flavor_delete(session: sqlalchemy.orm.Session,
                  controller: openStack.openstack_controller.OpenStackController,
                  flavor_name: str,
                  node_name: str):
    flavor = session.scalars(select(Flavor).where(Flavor.name == flavor_name)).one()
    if len(flavor.servers) == 0 and not flavor.is_default:
        backend_logger.info("커스텀 플레이버를 사용 중인 서버 없음")
        backend_logger.info("커스텀 플레이버 삭제")
        controller.delete_flavor(flavor_name=flavor_name, node_name=node_name)

        backend_logger.info("데이터베이스에 플레이버 삭제")
        target_node_flavors = session.scalars(select(NodeFlavor)
                                              .where(NodeFlavor.flavor_name == flavor_name)).all()
        # 외래키 제약 조건이 있으니 중간 테이블부터 삭제
        for target_node_flavor in target_node_flavors:
            controller.delete_flavor(flavor_name=target_node_flavor.flavor_name,
                                     node_name=target_node_flavor.node_name)
            session.delete(target_node_flavor)
        session.delete(flavor)


def network_rollback(session: sqlalchemy.orm.Session,
                     controller: openStack.openstack_controller.OpenStackController,
                     network_name: str,
                     node_name: str):
    network = session.scalars(select(Network).where(Network.name == network_name)).one()
    if not network.is_default:
        controller.remove_interface_from_router(router_name=openstack_config['router'],
                                                node_name=node_name,
                                                internal_subnet_name=subnet_name_creator(network_name))
        controller.delete_network(network_name=network_name, node_name=node_name)
