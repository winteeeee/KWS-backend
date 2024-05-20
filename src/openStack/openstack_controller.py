import openstack
from zunclient import client

from model.api_models import ServerCreateRequestDTO
from config.config import openstack_config
from util.utils import cloud_init_creator


class OpenStackController:
    def __init__(self):
        self._connection = openstack.connect(auth_url=openstack_config['auth_url'],
                                             username=openstack_config['username'],
                                             password=openstack_config['password'],
                                             project_name=openstack_config['project_name'],
                                             domain_name=openstack_config['domain_name'])
        self._zun_connection = client.Client(1,
                                             auth_url=openstack_config['auth_url'],
                                             username=openstack_config['username'],
                                             password=openstack_config['password'],
                                             project_name=openstack_config['project_name'],
                                             user_domain_name=openstack_config['domain_name'],
                                             project_domain_name=openstack_config['domain_name'])

    def monitoring_resources(self) -> dict:
        """
        UC- 서버 자원 현황 조회
        현재 시스템에 할당된 자원 정보들을 한 번에 반환합니다.
        자원 정보가 담긴 딕셔너리가 반환됩니다.

        딕셔너리의 정보는 아래와 같습니다.
        count: 현재 생성된 서버의 수
        vcpus: 현재 사용되는 cpu 코어 개수
        ram: 현재 사용되는 RAM 용량(GB)
        disk: 현재 사용되는 Disk 용량(GB)

        :return: 자원 딕셔너리
        """
        count = 0
        vcpus = 0
        ram = 0
        disk = 0

        servers = self._connection.compute.servers()

        for server in servers:
            count += 1
            vcpus += server.flavor["vcpus"]
            ram += server.flavor["ram"]
            disk += server.flavor["disk"]

        result = {
            "count": count,
            "vcpus": vcpus,
            "ram": float(ram / 1024),
            "disk": disk
        }

        return result

    def get_connection(self) -> openstack.connection.Connection:
        """
        어댑터 클래스 내부 Connection 객체를 반환합니다.
        Openstack SDK에 직접 접근할 필요가 있을 때 사용합니다.
        Openstack SDK의 자세한 내용은 아래 문서를 참고하세요.
        https://docs.openstack.org/openstacksdk/rocky/user/index.html#api-documentation

        :return: openstack.connection.Connection
        """
        return self._connection

    def find_server(self, server_name: str) -> openstack.compute.v2.server.Server:
        """
        서버 조회

        :param server_name: 조회할 서버명
        :return: openstack.compute.v2.server.Server
        """

        return self._connection.compute.find_server(server_name)

    def create_server(self, server_info: ServerCreateRequestDTO) -> openstack.compute.v2.server.Server:
        """
        UC-0101 서버 대여 / UC-0202 인스턴스 생성
        서버 정보를 바탕으로 인스턴스를 생성합니다.
        password가 입력된 경우 password로 접속이 가능하도록 설정하며,
        그게 아닌 경우 키페어를 할당합니다.

        :param server_info: 생성할 서버 정보
        :return: 서버 객체
        """

        kwargs = {
            "name": server_info.server_name,
            "image": self.find_image(server_info.image_name).id,
            "flavor": self.find_flavor(server_info.flavor_name).id,
            "network": self.find_network(server_info.network_name).id,
        }

        if server_info.password == "":
            keypair = self.find_key_pair(f"{server_info.server_name}_keypair")
            private_key = keypair.private_key
            kwargs["key_name"] = keypair.name
        else:
            private_key = ""

        cloud_init = cloud_init_creator(server_name=server_info.server_name,
                                        password=server_info.password,
                                        user_data=server_info.cloud_init)
        kwargs["userdata"] = cloud_init

        server = self._connection.create_server(**kwargs)
        self._connection.compute.wait_for_server(server)

        return server, private_key

    def allocate_floating_ip(self, server) -> str:
        return self._connection.add_auto_ip(server, wait=True)

    def delete_server(self, server_name: str, server_ip: str = None) -> None:
        """
        UC-0102 서버 반납 / UC-0203 인스턴스 삭제
        서버에 할당된 유동 IP, 키페어도 자동으로 삭제합니다.

        :param server_name: 삭제할 서버 이름
        :param server_ip: 삭제할 서버의 유동 아이피
        :return: 없음
        """

        server = self._connection.compute.find_server(server_name)

        if server is not None and server_ip is not None:
            floating_ips = self._connection.network.ips(server_id=server.id, device_id=server.id)
            for floating_ip in floating_ips:
                if floating_ip.floating_ip_address == server_ip:
                    self._connection.network.delete_ip(floating_ip.id)

            key_pair = self._connection.compute.find_keypair(f"{server_name}_keypair")
            if key_pair is not None:
                self._connection.compute.delete_keypair(key_pair)

            self._connection.compute.delete_server(server)

    def find_image(self, image_name: str) -> openstack.compute.v2.image.Image:
        """
        UC-0206 이미지 조회

        :param image_name: 이미지 이름
        :return: Image 객체
        """
        return self._connection.compute.find_image(image_name)

    def find_images(self):
        return self._connection.compute.images()

    def delete_image(self, image_name: str) -> None:
        """
        UC-0208 이미지 삭제

        :param image_name: 삭제할 이미지 이름
        :return: 없음
        """

        image = self.find_image(image_name)
        if image is not None:
            self._connection.compute.delete_image(image)
    
    def find_network(self, network_name: str) -> openstack.network.v2.network.Network:
        """
        UC-0210 네트워크 조회

        :param network_name: 조회할 네트워크 이름
        :return: openstack.network.v2.network.Network
        """
        return self._connection.network.find_network(network_name)

    def find_networks(self) -> list[openstack.network.v2.network.Network]:
        return self._connection.network.networks()

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
                       new_name: str = None,
                       external: bool = None) -> openstack.network.v2.network.Network:
        """
        UC-0212 네트워크 수정

        :param network_name: 수정할 네트워크 이름
        :param new_name: 수정할 네트워크의 새 이름
        :param external: 외부 네트워크 여부
        :return: openstack.network.v2.network.Network
        """

        target_network = self.find_network(network_name)
        return self._connection.network.update_network(network=target_network,
                                                       name=new_name if new_name is not None else network_name,
                                                       is_router_external=external if external is not None
                                                       else target_network.is_router_external)

    def delete_network(self, network_name: str) -> None:
        """
        UC-0213 네트워크 삭제

        :param network_name: 삭제할 네트워크 이름
        :return: 없음
        """

        network = self.find_network(network_name)
        if network is not None:
            self._connection.network.delete_network(network)
    
    def find_subnet(self, subnet_name: str) -> openstack.network.v2.subnet.Subnet:
        """
        UC-0214 서브넷 조회

        :param subnet_name: 조회할 서브넷 이름(ID도 가능)
        :return: openstack.network.v2.subnet.Subnet
        """

        return self._connection.network.find_subnet(subnet_name)

    def create_subnet(self,
                      subnet_name: str,
                      ip_version: int,
                      subnet_address: str,
                      subnet_gateway: str,
                      network_name: str) -> openstack.network.v2.subnet.Subnet:
        """
        UC-0215 서브넷 생성

        :param subnet_name: 생성할 서브넷 이름
        :param ip_version: IP 주소 버전
        :param subnet_address: 서브넷 주소
        :param subnet_gateway: 서브넷 게이트웨이 주소
        :param network_name: 연결할 네트워크 이름
        :return: openstack.network.v2.subnet.Subnet
        """

        return self._connection.network.create_subnet(name=subnet_name,
                                                      ip_version=ip_version,
                                                      cidr=subnet_address,
                                                      gateway_ip=subnet_gateway,
                                                      network_id=self.find_network(network_name).id,
                                                      dns_nameservers= ['8.8.8.8'])

    def update_subnet(self,
                      subnet_name: str,
                      new_name: str = None,
                      ip_version: int = None,
                      subnet_gateway: str = None) -> openstack.network.v2.subnet.Subnet:
        """
        UC-0216 서브넷 수정
        subnet_address는 read-only 속성이라서 수정 불가능합니다.
        subnet_address를 수정하고 싶다면 서브넷을 삭제 후 재생성 하세요.

        :param subnet_name: 변경할 서브넷의 이름
        :param new_name: 변경할 서브넷의 새 이름
        :param ip_version: 변경할 아이피 버전
        :param subnet_gateway: 변경할 서브넷 게이트웨이
        :return: openstack.network.v2.subnet.Subnet
        """

        target_subnet = self.find_subnet(subnet_name)
        return self._connection.network.update_subnet(subnet=target_subnet,
                                                      name=new_name if new_name is not None else subnet_name,
                                                      ip_version=ip_version if ip_version is not None
                                                      else target_subnet.ip_version,
                                                      gateway_ip=subnet_gateway if subnet_gateway is not None
                                                      else target_subnet.gateway_ip)

    def delete_subnet(self, subnet_name: str) -> None:
        """
        UC-0217 서브넷 삭제

        :param subnet_name: 삭제할 서브넷의 이름
        :return: 없음
        """

        subnet = self.find_subnet(subnet_name)
        if subnet is not None:
            self._connection.network.delete_subnet(subnet)

    def find_router(self, router_name: str) -> openstack.network.v2.router.Router:
        """
        UC-0218 라우터 조회

        :param router_name: 조회할 라우터 이름
        :return: openstack.network.v2.router.Router
        """

        return self._connection.network.find_router(router_name)

    def create_router(self,
                      router_name: str,
                      external_network_name: str = None,
                      external_subnet_name: str = None) -> openstack.network.v2.router.Router:
        """
        UC-0219 라우터 생성
        external_network_name과 external_subnet_name을 입력하면
        라우터 생성과 동시에 외부 네트워크의 게이트웨이와 연결합니다.
        기본적으로 서브넷 내부 게이트웨이 IP가 할당됩니다.

        내부 네트워크와의 연결은 add_interface_to_router 함수를 이용합니다.

        :param router_name: 생성할 라우터 이름
        :param external_network_name: 라우터와 연결할 외부 네트워크 이름
        :param external_subnet_name: 라우터의 게이트웨이로 선택할 외부 네트워크의 서브넷
        :return: openstack.network.v2.router.Router
        """

        if external_subnet_name and external_subnet_name is not None:
            external_network = self.find_network(external_network_name)
            external_gateway = {
                "network_id": external_network.id,
                "external_fixed_ips": [{
                    "subnet_id": self.find_subnet(external_subnet_name).id
                }]
            }

            router = self._connection.network.create_router(name=router_name,
                                                            external_gateway_info=external_gateway)
        else:
            router = self._connection.network.create_router(name=router_name)

        return router

    def add_interface_to_router(self, router_name: str, internal_subnet_name: str) \
            -> openstack.network.v2.router.Router:
        """
        라우터와 내부 네트워크를 연결합니다.

        :param router_name: 연결할 라우터 이름
        :param internal_subnet_name: 라우터와 연결할 내부 네트워크의 서브넷 이름
        :return:
        """

        return self._connection.network.add_interface_to_router(router=self.find_router(router_name),
                                                                subnet_id=self.find_subnet(internal_subnet_name).id)

    def remove_interface_from_router(self, router_name: str, internal_subnet_name: str) \
            -> None:
        return self._connection.network.remove_interface_from_router(router=self.find_router(router_name),
                                                                     subnet_id=self.find_subnet(internal_subnet_name).id)

    def update_router(self, router_name: str, new_name: str) -> openstack.network.v2.router.Router:
        """
        UC-0220 라우터 수정

        :param router_name: 변경할 라우터 이름
        :param new_name: 변경할 라우터의 새 이름
        :return: openstack.network.v2.router.Router
        """

        return self._connection.network.update_router(router=self.find_router(router_name),
                                                      name=new_name)

    def delete_router(self, router_name: str) -> None:
        """
        UC-0221 라우터 삭제

        :param router_name: 삭제할 라우터 이름
        :return: 없음
        """

        router = self.find_router(router_name)
        if router is not None:
            self._connection.network.delete_router(router)
    
    def find_flavor(self, flavor_name: str) -> openstack.compute.v2.flavor.Flavor:
        """
        UC-0222 플레이버 조회

        :param flavor_name: 조회할 플레이버 이름
        :return: openstack.compute.v2.flavor.Flavor
        """
        return self._connection.compute.find_flavor(flavor_name)

    def find_flavors(self) -> list[openstack.compute.v2.flavor.Flavor]:
        return self._connection.compute.flavors()

    def create_flavor(self,
                      flavor_name: str,
                      vcpus: int,
                      ram: int,
                      disk: int) -> openstack.compute.v2.flavor.Flavor:
        """
        UC-0223 플레이버 생성

        :param flavor_name: 생성할 플레이버 이름
        :param vcpus: 플레이버의 vcpu 수
        :param ram: 플레이버의 RAM 용량(MB)
        :param disk: 플레이버의 디스크 용량(GB)
        :return: openstack.compute.v2.flavor.Flavor
        """

        return self._connection.compute.create_flavor(name=flavor_name, vcpus=vcpus, ram=ram, disk=disk)

    def delete_flavor(self, flavor_name: str) -> None:
        """
        UC-0224 플레이버 삭제

        :param flavor_name: 삭제할 플레이버 이름
        :return: 없음
        """

        flavor = self.find_flavor(flavor_name)
        if flavor is not None:
            self._connection.compute.delete_flavor(flavor)

    def create_key_pair(self, keypair_name) -> openstack.compute.v2.keypair.Keypair:
        """
        키 페어를 생성하고 개인키 파일을 생성합니다.

        :param keypair_name:
        :return: openstack.compute.v2.keypair.Keypair
        """

        keypair = self._connection.compute.create_keypair(name=keypair_name)
        return keypair

    def find_key_pair(self, keypair_name) -> openstack.compute.v2.keypair.Keypair:
        """
        해당 키 페어 이름을 가진 키 페어를 찾아 키 페어 객체를 반환합니다.
        없다면 해당 이름을 지닌 키 페어를 새로 생성합니다.

        :param keypair_name: 조회할 키 페어 이름
        :return: openstack.compute.v2.keypair.Keypair
        """

        keypair = self._connection.compute.find_keypair(keypair_name)

        if not keypair:
            keypair = self.create_key_pair(keypair_name)

        return keypair

    def find_ports(self, network_id: str):
        return self._connection.network.ports(network_id=network_id)

    def create_container(self,
                         container_name: str,
                         image_name: str,
                         env: str = None,
                         cmd: str = None):
        """
        컨테이너를 생성합니다.

        :param container_name: 생성할 컨테이너의 이름
        :param image_name: 도커 허브에서 가져올 이미지 이름
        :param env: 덮어 씌울 환경 변수
        :param cmd: 덮어 씌울 명령어
        :return: 생성된 컨테이너 인스턴스
        """

        if self.find_container(container_name) is not None:
            return None

        return self._zun_connection.containers.run(name=container_name,
                                                   image=image_name,
                                                   environment=env,
                                                   command=cmd)

    def find_container(self, container_name: str):
        """
        컨테이너 인스턴스를 반환합니다.

        :param container_name: 반환할 컨테이너 이름
        :return: 반환한 컨테이너 인스턴스
        """

        try:
            return self._zun_connection.containers.get(container_name)
        except:
            return None

    def delete_container(self, container_name: str):
        """
        컨테이너를 삭제합니다.

        :param container_name: 삭제할 컨테이너 이름
        :return: 없음
        """

        if self.find_container(container_name) is not None:
            self._zun_connection.containers.delete(id=container_name, force=True)
