import openstack

from Model.models import ServerInfo


class OpenStackController:
    def __init__(self, cloud: str):
        self._connection = openstack.connect(cloud=cloud)

    def create_server(self, server_info: ServerInfo):
        image = self._connection.compute.find_image(server_info.image_name)
        flavor = self._connection.compute.find_flavor(server_info.flavor_name)
        network = self._connection.compute.find_network(server_info.network_name)
        keypair = self._connection.compute.find_keypair(server_info.keypair_name)

        server = self._connection.create_server(
            name=server_info.server_name,
            image_id=image.id,
            flavor_id=flavor.id,
            networks=[{"uuid": network.id}],
            key_name=keypair.name,
        )
        server = self._connection.compute.wait_for_server(server)

        return server

    def allocate_floating_ip(self, server: object):
        floating_ip = self._connection.add_auto_ip(server)
        return floating_ip
