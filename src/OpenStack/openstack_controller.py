import openstack


class OpenStackController:
    def __init__(self, cloud: str):
        self._connection = openstack.connect(cloud=cloud)

    def create_server(self,
                      server_name: str,
                      image_name: str,
                      flavor_name: str,
                      network_name: str,
                      keypair_name: str):
        image = self._connection.compute.find_image(image_name)
        flavor = self._connection.compute.find_flavor(flavor_name)
        network = self._connection.compute.find_network(network_name)
        keypair = self._connection.compute.find_keypair(keypair_name)

        server = self._connection.create_server(
            name=server_name,
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
