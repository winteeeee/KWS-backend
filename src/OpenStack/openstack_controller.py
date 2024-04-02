import openstack

from Model.models import ServerInfo


class OpenStackController:
    def __init__(self, cloud: str):
        self._connection = openstack.connect(cloud=cloud)

    def monitoring_resources(self) -> dict:
        # TODO UC-0104 서버 대여 현황 조회
        pass

    def find_server(self, server_name: str) -> object:
        return self._connection.compute.find_server(server_name)

    def create_server(self, server_info: ServerInfo) -> openstack.compute.v2.server.Server:
        """
        UC-0101 서버 대여
        UC-0202 인스턴스 생성

        :param server_info: 생성할 서버 정보
        :return: 서버 객체
        """
        image = self.find_image(server_info.image_name)
        flavor = self.find_flavor(server_info.flavor_name)
        network = self.find_network(server_info.network_name)
        keypair = self.find_key_pair(f"{ServerInfo.server_name}_keypair")

        server = self._connection.create_server(
            name=server_info.server_name,
            image_id=image.id,
            flavor_id=flavor.id,
            networks=[{"uuid": network.id}],
            key_name=keypair.name,
        )

        server = self._connection.compute.wait_for_server(server)
        self._connection.add_auto_ip(server)

        return server

    """
    def create_server(self, server_info: ServerInfo) -> openstack.compute.v2.server.Server:
        image = self.find_image(server_info.image_name)
        flavor = self.find_flavor(server_info.flavor_name)
        network = self.find_network(server_info.network_name)

        server = self._connection.create_server(
            name=server_info.server_name,
            image_id=image.id,
            flavor_id=flavor.id,
            networks=[{"uuid": network.id}],
        )
        server = self._connection.compute.wait_for_server(server)
        self._connection.add_auto_ip(server)

        if server_info.password:
            self.allocate_password(server, server_info.password)
        else:
            keypair_name = self.create_key_pair()
            self.allocate_key_pair(server, keypair_name)

        return server
    """

    def delete_server(self, server_name: str) -> None:
        # TODO UC-0102 서버 반납 / UC-0203 인스턴스 삭제
        server = self._connection.compute.find_server(server_name)
        floating_ips = self._connection.network.ips(server_id=server.id, device_id=server.id)

        for floating_ip in floating_ips:
            self._connection.network.delete_ip(floating_ip.id)

        self._connection.compute.delete_server(server)
    """
    def create_floating_ip(self) -> str:
        # TODO UC-0204 유동 IP 할당
        # TODO 외부 네트워크에서 유동 IP 생성. 생성한 유동 IP 반환
        # 서버 유동 IP 자동 할당


    def allocate_floating_ip(self, server: object, floating_ip: str) -> None:
        # TODO UC-0205 유동 IP 연결
        # TODO 인자로 넘겨받은 유동 IP를 서버에 할당. 반환값 없음
        pass
        # floating_ip = self._connection.add_auto_ip(server)
        # return floating_ip
    """
    def find_image(self, image_name: str) -> openstack.compute.v2.image.Image:
        """
        UC-0206 이미지 조회

        :param image_name: 이미지 이름
        :return: Image 객체
        """
        return self._connection.compute.find_image(image_name)

    def create_image(self, image_name: str) -> openstack.compute.v2.image.Image:
        # TODO UC-0206 이미지 생성
        pass

    def update_image(self, image_name: str) -> None:
        # TODO UC-0207 이미지 수정
        pass

    def delete_image(self, image_name: str) -> None:
        # TODO UC-0208 이미지 삭제
        pass
    
    def find_network(self, network_name: str) -> openstack.network.v2.network.Network:
        """
        UC-0210 네트워크 조회

        :param network_name: 이미지 이름
        :return: Network 객체
        """
        return self._connection.network.find_network(network_name)

    def create_network(self,
                       network_name: str,
                       external: bool = False) -> openstack.network.v2.network.Network:
        """
        UC-0211 네트워크 생성

        :param network_name: 생성할 네트워크 이름
        :param external: 외부 네트워크 여부
        :return: openstack.network.v2.network.Network
        """
        return self._connection.network.create_network(name=network_name, is_router_external=external)

    def update_network(self,
                       network_name: str,
                       external: bool) -> openstack.network.v2.network.Network:
        """
        UC-0212 네트워크 수정

        :param network_name: 수정할 네트워크 이름
        :param external: 외부 네트워크 여부
        :return: openstack.network.v2.network.Network
        """

        return self._connection.network.update_network(self.find_network(network_name), is_router_external=external)

    def delete_network(self, network_name: str) -> None:
        """
        UC-0213 네트워크 삭제

        :param network_name: 삭제할 네트워크 이름
        :return: 없음
        """

        self._connection.network.delete_network(self.find_network(network_name))
    
    def find_subnet(self, subnet_name: str) -> object:
        # TODO UC-0214 서브넷 조회
        pass
    
    def create_subnet(self, subnet_name: str) -> object:
        # TODO UC-0215 서브넷 생성
        pass

    def update_subnet(self, subnet_name: str) -> None:
        # TODO UC-0216 서브넷 수정
        pass

    def delete_subnet(self, subnet_name: str) -> None:
        # TODO UC-0217 서브넷 삭제
        pass

    def find_router(self, router_name: str) -> object:
        # TODO UC-0218 라우터 조회
        pass

    def create_router(self, router_name: str) -> object:
        # TODO UC-0219 라우터 생성
        pass

    def update_router(self, router_name: str) -> None:
        # TODO UC-0220 라우터 수정
        pass

    def delete_router(self, router_name: str) -> None:
        # TODO UC-0221 라우터 삭제
        pass
    
    def find_flavor(self, flavor_name: str) -> openstack.compute.v2.flavor.Flavor:
        """
        UC-0222 플레이버 조회

        :param flavor_name: 플레이버 이름
        :return: Flavor 객체
        """
        return self._connection.compute.find_flavor(flavor_name)

    def create_flavor(self, flavor_name: str) -> openstack.compute.v2.flavor.Flavor:
        # TODO UC-0223 플레이버 생성
        pass

    def delete_flavor(self, flavor_name: str) -> None:
        # TODO UC-0224 플레이버 삭제
        pass

    def allocate_password(self, server: object, password: str) -> None:
        # TODO 서버의 password 할당
        pass

    def create_key_pair(self, keypair_name) -> str:
        # TODO 키 페어 생성. 키페어 name 반환
        # 변경 사항
        # 키페이 이름 : server_name + keypair
        # 반환 : 일단 개인키 파일에 저장

        keypair = self._connection.compute.create_keypair(name=keypair_name)

        with open(f"{keypair_name}.pem", "w") as f:
            f.write(keypair.private_key)

        return keypair

    """
    def allocate_key_pair(self, server: object, key_pair_name: str) -> None:
        # TODO 키페어를 서버에 할당. 반환값 없음
        pass
    """
    def find_key_pair(self, keypair_name):
        # TODO 키페어 반환 (개인키, 공개키)
        keypair = self._connection.compute.find_keypair(keypair_name)

        if not keypair:
            keypair = self.create_key_pair(keypair_name)

        return keypair

    def take_snapshot(self, server: object):
        # TODO 서버의 스냅샷 생성
        pass
