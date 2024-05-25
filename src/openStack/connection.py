import openstack
from zunclient import client

from config.config import node_config, openstack_config


class Connection:
    def __init__(self, auth_url):
        self.connection = openstack.connect(auth_url=auth_url,
                                            username=openstack_config['username'],
                                            password=openstack_config['password'],
                                            project_name=openstack_config['project_name'],
                                            domain_name=openstack_config['domain_name'])
        self.zun_connection = client.Client(1,
                                            auth_url=auth_url,
                                            username=openstack_config['username'],
                                            password=openstack_config['password'],
                                            project_name=openstack_config['project_name'],
                                            user_domain_name=openstack_config['domain_name'],
                                            project_domain_name=openstack_config['domain_name'])


def get_connections() -> dict[str, Connection]:
    connections = {}
    for node in node_config['nodes']:
        connections[node['name']] = Connection(node['auth_url'])

    return connections
