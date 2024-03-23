import openstack

connection = openstack.connect(cloud='openstack')

server_name = "test-server"
image_name = "jammy-server"
flavor_name = "m1.small"
network_name = "private"
keypair_name = "cloud_key"


def create_server(conn):
    image = conn.compute.find_image(image_name)
    flavor = conn.compute.find_flavor(flavor_name)
    network = conn.network.find_network(network_name)
    keypair = conn.compute.find_keypair(keypair_name)

    server = conn.compute.create_server(
        name=server_name,
        image_id=image.id,
        flavor_id=flavor.id,
        networks=[{"uuid": network.id}],
        key_name=keypair.name,
    )

    return server


server = create_server(connection)
server = connection.compute.wait_for_server(server)
floating_ip = connection.add_auto_ip(server)

print(floating_ip)
