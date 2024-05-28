import openStack.openstack_controller
from util.utils import gateway_extractor
from config.config import openstack_config


def network_isolation(controller: openStack.openstack_controller.OpenStackController,
                      node_name,
                      backend_logger,
                      network_name,
                      subnet_cidr):
    backend_logger.info(f"[{node_name}]: 네트워크 분리 중")
    subnet_name = f'{network_name}_subnet'

    try:
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
    except Exception as e:
        backend_logger.error(e)
        network_delete(controller=controller,
                       node_name=node_name,
                       network_name=network_name,
                       backend_logger=backend_logger)


def network_delete(controller: openStack.openstack_controller.OpenStackController,
                   node_name,
                   backend_logger,
                   network_name):
    backend_logger.info(f"[{node_name}] : 네트워크 삭제 프로세스 시작")
    subnet_name = f'{network_name}_subnet'

    controller.remove_interface_from_router(router_name=openstack_config['router'],
                                            node_name=node_name,
                                            internal_subnet_name=subnet_name)
    controller.delete_network(network_name=network_name, node_name=node_name)
