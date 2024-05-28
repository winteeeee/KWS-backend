import time
import openstack

from util.utils import cloud_init_creator
from util.logger import get_logger
from openStack.connection import get_connections, Connection


class OpenStackController:
    def __init__(self):
        self._connections = get_connections()
        self._logger = get_logger(name='openstack_controller', log_level='INFO', save_path="./log/openStack")

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super().__new__(cls)
        return cls.instance

    def kws_init(self, node_name: str):
        pass

    def monitoring_resources(self, node_name, logger_on: bool = True) -> dict:
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
        if logger_on:
            self._logger.info(f'[{node_name}] : monitoring_resources 실행')

        count = 0
        vcpus = 0
        ram = 0
        disk = 0

        servers = self._connections[node_name].connection.compute.servers()

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

    def get_connections(self, logger_on: bool = True) -> dict[str, Connection]:
        """
        어댑터 클래스 내부 Connection 객체를 반환합니다.
        Openstack SDK에 직접 접근할 필요가 있을 때 사용합니다.
        Openstack SDK의 자세한 내용은 아래 문서를 참고하세요.
        https://docs.openstack.org/openstacksdk/rocky/user/index.html#api-documentation

        오픈스택 컨트롤러는 내부에서 노드들의 커넥션을 딕셔너리로 관리합니다.
        {'노드명': '커넥션 객체'}로 저장되어 노드명으로 접근하면 됩니다.
        커넥션 객체 내부는 nova, neutron 등 오픈스택의 기본 모듈에 접근하기 위한
        오픈스택 커넥션(connection)과 컨테이너를 담당하는 zun에 접근하기 위한
        준 커넥션(zun_connection)이 존재합니다.

        :return: dict[str, Connection]
        """
        if logger_on:
            self._logger.info(f'get_connections 실행')
        return self._connections

    def find_server(self, server_name: str, node_name: str, logger_on: bool = True) -> openstack.compute.v2.server.Server:
        """
        서버 조회

        :param server_name: 조회할 서버명
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: openstack.compute.v2.server.Server
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : find_server 실행')
        return self._connections[node_name].connection.compute.find_server(server_name)

    def create_server(self,
                      server_name: str,
                      image_name: str,
                      flavor_name: str,
                      network_name: str,
                      password: str,
                      cloud_init: str,
                      node_name: str,
                      logger_on: bool = True) -> openstack.compute.v2.server.Server:
        """
        UC-0101 서버 대여 / UC-0202 인스턴스 생성
        서버 정보를 바탕으로 인스턴스를 생성합니다.
        password가 입력된 경우 password로 접속이 가능하도록 설정하며,
        그게 아닌 경우 키페어를 할당합니다.

        :param server_name: 생성할 서버의 이름
        :param image_name: 생성할 서버의 이미지 이름
        :param flavor_name: 생성할 서버의 플레이버 이름
        :param network_name: 생성할 서버의 네트워크 이름
        :param password: 생성할 서버의 비밀번호 None일 경우 키페어 자동 할당
        :param cloud_init: 생성할 서버에 적용할 cloud-init
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: 서버 객체
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : create_server 실행')

        kwargs = {
            "name": server_name,
            "image": self.find_image(image_name, node_name=node_name,logger_on=False).id,
            "flavor": self.find_flavor(flavor_name, node_name=node_name, logger_on=False).id,
            "network": self.find_network(network_name, node_name=node_name, logger_on=False).id,
        }

        if password is None:
            if logger_on:
                self._logger.info(f"[{node_name}] : 인스턴스에 키페어 할당")
            keypair = self.find_key_pair(f"{server_name}_keypair", node_name=node_name, logger_on=False)
            private_key = keypair.private_key
            kwargs["key_name"] = keypair.name
        else:
            if logger_on:
                self._logger.info(f"[{node_name}] : 인스턴스에 비밀번호 할당")
            private_key = ""

        cloud_init = cloud_init_creator(server_name=server_name,
                                        password=password,
                                        user_data=cloud_init)
        kwargs["userdata"] = cloud_init

        if logger_on:
            self._logger.info(f"[{node_name}] : 서버 생성 중")
        server = self._connections[node_name].connection.create_server(**kwargs)
        if logger_on:
            self._logger.info(f"[{node_name}] : 서버 가동 대기 중")
        self._connections[node_name].connection.compute.wait_for_server(server)

        return server, private_key

    def allocate_floating_ip(self, server, node_name: str, logger_on: bool = True) -> str:
        if logger_on:
            self._logger.info(f'[{node_name}] : allocate_floating_ip 실행')
        return self._connections[node_name].connection.add_auto_ip(server, wait=True)

    def delete_server(self, server_name: str, node_name: str, server_ip: str = None, logger_on: bool = True) -> None:
        """
        UC-0102 서버 반납 / UC-0203 인스턴스 삭제
        서버에 할당된 유동 IP, 키페어도 자동으로 삭제합니다.

        :param server_name: 삭제할 서버 이름
        :param server_ip: 삭제할 서버의 유동 아이피
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: 없음
        """

        if logger_on:
            self._logger.info(f'[{node_name}] : delete_server 실행')
        server = self._connections[node_name].connection.compute.find_server(server_name)

        if server is not None and server_ip is not None:
            if logger_on:
                self._logger.info(f'[{node_name}] : 유동 IP 삭제 중')
            floating_ips = self._connections[node_name].connection.network.ips(server_id=server.id, device_id=server.id)
            for floating_ip in floating_ips:
                if floating_ip.floating_ip_address == server_ip:
                    self._connections[node_name].connection.network.delete_ip(floating_ip.id)

            key_pair = self._connections[node_name].connection.compute.find_keypair(f"{server_name}_keypair")
            if key_pair is not None:
                if logger_on:
                    self._logger.info(f'[{node_name}] : 키페어 삭제 중')
                self._connections[node_name].connection.compute.delete_keypair(key_pair)

            self._connections[node_name].connection.compute.delete_server(server)

    def find_image(self, image_name: str, node_name: str, logger_on: bool = True) -> openstack.compute.v2.image.Image:
        """
        UC-0206 이미지 조회

        :param image_name: 이미지 이름
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: Image 객체
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : find_image 실행')
        return self._connections[node_name].connection.compute.find_image(image_name)

    def find_images(self, node_name: str, logger_on: bool = True):
        """
        시스템에 존재하는 모든 이미지 조회

        :return: 이미지 제너레이터
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : find_images 실행')
        return self._connections[node_name].connection.compute.images()

    def delete_image(self, image_name: str, node_name: str, logger_on: bool = True) -> None:
        """
        UC-0208 이미지 삭제

        :param image_name: 삭제할 이미지 이름
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: 없음
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : delete_image 실행')

        image = self.find_image(image_name=image_name, node_name=node_name, logger_on=False)
        if image is not None:
            self._connections[node_name].connection.compute.delete_image(image)
    
    def find_network(self, network_name: str, node_name: str, logger_on: bool = True) -> openstack.network.v2.network.Network:
        """
        UC-0210 네트워크 조회

        :param network_name: 조회할 네트워크 이름
        :return: openstack.network.v2.network.Network
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : find_network 실행')
        return self._connections[node_name].connection.network.find_network(network_name)

    def find_networks(self, node_name: str, logger_on: bool = True) -> list[openstack.network.v2.network.Network]:
        """
        시스템에 존재하는 모든 네트워크 조회

        :return: 네트워크 제너레이터
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : find_networks 실행')
        return self._connections[node_name].connection.network.networks()

    def create_network(self,
                       network_name: str,
                       node_name: str,
                       external: bool = False,
                       logger_on: bool = True) -> openstack.network.v2.network.Network:
        """
        UC-0211 네트워크 생성

        :param network_name: 생성할 네트워크 이름
        :param external: 외부 네트워크 여부
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: openstack.network.v2.network.Network
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : create_network 실행')
        return self._connections[node_name].connection.network.create_network(name=network_name, is_router_external=external)

    def update_network(self,
                       network_name: str,
                       node_name: str,
                       new_name: str = None,
                       external: bool = None,
                       logger_on: bool = True) -> openstack.network.v2.network.Network:
        """
        UC-0212 네트워크 수정

        :param network_name: 수정할 네트워크 이름
        :param new_name: 수정할 네트워크의 새 이름
        :param external: 외부 네트워크 여부
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: openstack.network.v2.network.Network
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : update_network 실행')
        target_network = self.find_network(network_name=network_name, node_name=node_name, logger_on=False)
        return self._connections[node_name].connection.network.update_network(network=target_network,
                                                                              name=new_name if new_name is not None else network_name,
                                                                              is_router_external=external if external is not None
                                                                              else target_network.is_router_external)

    def delete_network(self, network_name: str, node_name: str, logger_on: bool = True) -> None:
        """
        UC-0213 네트워크 삭제

        :param network_name: 삭제할 네트워크 이름
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: 없음
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : delete_network 실행')
        network = self.find_network(network_name=network_name, node_name=node_name, logger_on=False)
        if network is not None:
            self._connections[node_name].connection.network.delete_network(network)
    
    def find_subnet(self, subnet_name: str, node_name: str, logger_on: bool = True) -> openstack.network.v2.subnet.Subnet:
        """
        UC-0214 서브넷 조회

        :param subnet_name: 조회할 서브넷 이름(ID도 가능)
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: openstack.network.v2.subnet.Subnet
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : find_subnet 실행')
        return self._connections[node_name].connection.network.find_subnet(subnet_name)

    def create_subnet(self,
                      subnet_name: str,
                      node_name: str,
                      ip_version: int,
                      subnet_address: str,
                      subnet_gateway: str,
                      network_name: str,
                      logger_on: bool = True) -> openstack.network.v2.subnet.Subnet:
        """
        UC-0215 서브넷 생성

        :param subnet_name: 생성할 서브넷 이름
        :param ip_version: IP 주소 버전
        :param subnet_address: 서브넷 주소
        :param subnet_gateway: 서브넷 게이트웨이 주소
        :param network_name: 연결할 네트워크 이름
        :return: openstack.network.v2.subnet.Subnet
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : create_subnet 실행')
        return self._connections[node_name].connection.network.create_subnet(name=subnet_name,
                                                                             ip_version=ip_version,
                                                                             cidr=subnet_address,
                                                                             gateway_ip=subnet_gateway,
                                                                             network_id=self.find_network(network_name=network_name,
                                                                                                          node_name=node_name,
                                                                                                          logger_on=False).id,
                                                                             dns_nameservers=['8.8.8.8'])

    def update_subnet(self,
                      subnet_name: str,
                      node_name: str,
                      new_name: str = None,
                      ip_version: int = None,
                      subnet_gateway: str = None,
                      logger_on: bool = True) -> openstack.network.v2.subnet.Subnet:
        """
        UC-0216 서브넷 수정
        subnet_address는 read-only 속성이라서 수정 불가능합니다.
        subnet_address를 수정하고 싶다면 서브넷을 삭제 후 재생성 하세요.

        :param subnet_name: 변경할 서브넷의 이름
        :param new_name: 변경할 서브넷의 새 이름
        :param ip_version: 변경할 아이피 버전
        :param subnet_gateway: 변경할 서브넷 게이트웨이
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: openstack.network.v2.subnet.Subnet
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : update_subnet 실행')
        target_subnet = self.find_subnet(subnet_name=subnet_name, node_name=node_name, logger_on=False)
        return self._connections[node_name].connection.network.update_subnet(subnet=target_subnet,
                                                                             name=new_name if new_name is not None else subnet_name,
                                                                             ip_version=ip_version if ip_version is not None
                                                                             else target_subnet.ip_version,
                                                                             gateway_ip=subnet_gateway if subnet_gateway is not None
                                                                             else target_subnet.gateway_ip)

    def delete_subnet(self, subnet_name: str, node_name: str, logger_on: bool = True) -> None:
        """
        UC-0217 서브넷 삭제

        :param subnet_name: 삭제할 서브넷의 이름
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: 없음
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : delete_subnet 실행')
        subnet = self.find_subnet(subnet_name=subnet_name, node_name=node_name, logger_on=False)
        if subnet is not None:
            self._connections[node_name].connection.network.delete_subnet(subnet)

    def find_router(self, router_name: str, node_name: str, logger_on: bool = True) -> openstack.network.v2.router.Router:
        """
        UC-0218 라우터 조회

        :param router_name: 조회할 라우터 이름
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: openstack.network.v2.router.Router
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : find_router 실행')
        return self._connections[node_name].connection.network.find_router(router_name)

    def create_router(self,
                      router_name: str,
                      node_name: str,
                      external_network_name: str = None,
                      external_subnet_name: str = None,
                      logger_on: bool = True) -> openstack.network.v2.router.Router:
        """
        UC-0219 라우터 생성
        external_network_name과 external_subnet_name을 입력하면
        라우터 생성과 동시에 외부 네트워크의 게이트웨이와 연결합니다.
        기본적으로 서브넷 내부 게이트웨이 IP가 할당됩니다.

        내부 네트워크와의 연결은 add_interface_to_router 함수를 이용합니다.

        :param router_name: 생성할 라우터 이름
        :param external_network_name: 라우터와 연결할 외부 네트워크 이름
        :param external_subnet_name: 라우터의 게이트웨이로 선택할 외부 네트워크의 서브넷
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: openstack.network.v2.router.Router
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : create_router 실행')
        if external_subnet_name and external_subnet_name is not None:
            if logger_on:
                self._logger.info(f'[{node_name}] : 외부 게이트웨이 연결')
            external_network = self.find_network(network_name=external_network_name,
                                                 node_name=node_name,
                                                 logger_on=False)
            external_gateway = {
                "network_id": external_network.id,
                "external_fixed_ips": [{
                    "subnet_id": self.find_subnet(subnet_name=external_subnet_name,
                                                  node_name=node_name,
                                                  logger_on=False).id
                }]
            }

            router = self._connections[node_name].connection.network.create_router(name=router_name,
                                                                                   external_gateway_info=external_gateway)
        else:
            router = self._connections[node_name].connection.network.create_router(name=router_name)

        return router

    def add_interface_to_router(self, router_name: str,
                                internal_subnet_name: str,
                                node_name: str,
                                logger_on: bool = True) -> openstack.network.v2.router.Router:
        """
        라우터와 내부 네트워크를 연결합니다.

        :param router_name: 연결할 라우터 이름
        :param internal_subnet_name: 라우터와 연결할 내부 네트워크의 서브넷 이름
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return:
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : add_interface_to_router 실행')
        return self._connections[node_name].connection.network.add_interface_to_router(router=self.find_router(router_name=router_name,
                                                                                                               node_name=node_name,
                                                                                                               logger_on=False),
                                                                                       subnet_id=self.find_subnet(subnet_name=internal_subnet_name,
                                                                                                                  node_name=node_name,
                                                                                                                  logger_on=False).id)

    def remove_interface_from_router(self, router_name: str,
                                     node_name: str,
                                     internal_subnet_name: str,
                                     logger_on: bool = True) -> None:
        """
        라우터에서 인터페이스 제거

        :param router_name: 라우터 이름
        :param internal_subnet_name: 제거할 인터페이스의 서브넷 이름
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: 없음
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : remove_interface_from_router 실행')
        try:
            self._connections[node_name].connection.network.remove_interface_from_router(router=self.find_router(router_name=router_name,
                                                                                                                 node_name=node_name,
                                                                                                                 logger_on=False),
                                                                                         subnet_id=self.find_subnet(subnet_name=internal_subnet_name,
                                                                                                                    node_name=node_name,
                                                                                                                    logger_on=True).id)
        except:
            pass

    def update_router(self,
                      router_name: str,
                      new_name: str,
                      node_name: str,
                      logger_on: bool = True) -> openstack.network.v2.router.Router:
        """
        UC-0220 라우터 수정

        :param router_name: 변경할 라우터 이름
        :param new_name: 변경할 라우터의 새 이름
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: openstack.network.v2.router.Router
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : update_router 실행')
        return self._connections[node_name].connection.network.update_router(router=self.find_router(router_name=router_name,
                                                                                                     node_name=node_name,
                                                                                                     logger_on=False),
                                                                             name=new_name)

    def delete_router(self, router_name: str, node_name: str, logger_on: bool = True) -> None:
        """
        UC-0221 라우터 삭제

        :param router_name: 삭제할 라우터 이름
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: 없음
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : delete_router 실행')
        router = self.find_router(router_name=router_name, node_name=node_name, logger_on=False)
        if router is not None:
            self._connections[node_name].connection.network.delete_router(router)
    
    def find_flavor(self,
                    flavor_name: str,
                    node_name: str,
                    logger_on: bool = True) -> openstack.compute.v2.flavor.Flavor:
        """
        UC-0222 플레이버 조회

        :param flavor_name: 조회할 플레이버 이름
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: openstack.compute.v2.flavor.Flavor
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : find_flavor 실행')
        return self._connections[node_name].connection.compute.find_flavor(flavor_name)

    def find_flavors(self, node_name: str, logger_on: bool = True) -> list[openstack.compute.v2.flavor.Flavor]:
        """
        시스템에 존재하는 모든 플레이버 조회

        :return: 플레이버 제너레이터
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : find_flavors 실행')
        return self._connections[node_name].connection.compute.flavors()

    def create_flavor(self,
                      flavor_name: str,
                      node_name: str,
                      vcpus: int,
                      ram: int,
                      disk: int,
                      logger_on: bool = True) -> openstack.compute.v2.flavor.Flavor:
        """
        UC-0223 플레이버 생성

        :param flavor_name: 생성할 플레이버 이름
        :param vcpus: 플레이버의 vcpu 수
        :param ram: 플레이버의 RAM 용량(MB)
        :param disk: 플레이버의 디스크 용량(GB)
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: openstack.compute.v2.flavor.Flavor
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : create_flavor 실행')
        return self._connections[node_name].connection.compute.create_flavor(name=flavor_name,
                                                                             vcpus=vcpus,
                                                                             ram=ram,
                                                                             disk=disk)

    def delete_flavor(self, flavor_name: str, node_name: str, logger_on: bool = True) -> None:
        """
        UC-0224 플레이버 삭제

        :param flavor_name: 삭제할 플레이버 이름
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: 없음
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : delete_flavor 실행')
        flavor = self.find_flavor(flavor_name=flavor_name, node_name=node_name, logger_on=False)
        if flavor is not None:
            self._connections[node_name].connection.compute.delete_flavor(flavor)

    def create_key_pair(self,
                        keypair_name: str,
                        node_name: str,
                        logger_on: bool = True) -> openstack.compute.v2.keypair.Keypair:
        """
        키 페어를 생성하고 개인키 파일을 생성합니다.

        :param keypair_name: 키페어 이름
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: openstack.compute.v2.keypair.Keypair
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : create_key_pair 실행')
        keypair = self._connections[node_name].connection.compute.create_keypair(name=keypair_name)
        return keypair

    def find_key_pair(self,
                      keypair_name: str,
                      node_name: str,
                      logger_on: bool = True) -> openstack.compute.v2.keypair.Keypair:
        """
        해당 키 페어 이름을 가진 키 페어를 찾아 키 페어 객체를 반환합니다.
        없다면 해당 이름을 지닌 키 페어를 새로 생성합니다.

        :param keypair_name: 조회할 키 페어 이름
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: openstack.compute.v2.keypair.Keypair
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : find_key_pair 실행')
        keypair = self._connections[node_name].connection.compute.find_keypair(keypair_name)

        if not keypair:
            keypair = self.create_key_pair(keypair_name=keypair_name, node_name=node_name)

        return keypair

    def find_ports(self, network_id: str, node_name: str, logger_on: bool = True):
        """
        네트워크에 존재하는 모든 포트 조회

        :param network_id: 네트워크 아이디
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: 플레이버 제너레이터
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : find_ports 실행')
        return self._connections[node_name].connection.network.ports(network_id=network_id)

    def create_container(self,
                         container_name: str,
                         image_name: str,
                         network_name: str,
                         node_name: str,
                         env: dict = None,
                         cmd: list = None,
                         timeout: int = 10,
                         logger_on = True):
        """
        컨테이너를 생성합니다.

        :param container_name: 생성할 컨테이너의 이름
        :param image_name: 도커 허브에서 가져올 이미지 이름
        :param network_name: 컨테이너에 연결될 네트워크 이름
        :param env: 덮어 씌울 환경변수
        :param cmd: 덮어 씌울 명령어
        :param timeout: 컨테이너 실행 대기 타임아웃
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: 생성된 컨테이너 인스턴스
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : create_container 실행')
        if self.find_container(container_name=container_name, node_name=node_name, logger_on=False) is not None:
            return None

        container = self._connections[node_name].zun_connection.containers.run(name=container_name,
                                                                               image=image_name,
                                                                               environment=env,
                                                                               command=cmd,
                                                                               nets=[{'network': network_name}])

        timeout_count = 0
        if logger_on:
            self._logger.info(f'[{node_name}] : 컨테이너 준비 대기 중')
        while container.status == 'Creating' or timeout_count <= timeout:
            container = self.find_container(container_name=container_name, node_name=node_name, logger_on=False)
            time.sleep(1)
            timeout_count += 1

        if timeout_count <= timeout:
            raise Exception('컨테이너가 Running 상태가 아닙니다.')

        return container

    def find_container(self, container_name: str, node_name: str, logger_on: bool = True):
        """
        컨테이너 인스턴스를 반환합니다.

        :param container_name: 반환할 컨테이너 이름
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :return: 반환한 컨테이너 인스턴스
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : find_container 실행')
        try:
            return self._connections[node_name].zun_connection.containers.get(container_name)
        except:
            return None

    def delete_container(self, container_name: str, node_name: str, logger_on: bool = True, timeout:int = 10):
        """
        컨테이너를 삭제합니다.

        :param container_name: 삭제할 컨테이너 이름
        :param node_name: 접근할 노드명
        :param logger_on: 로그 온/오프
        :param timeout: 컨테이너 삭제 대기 타임아웃
        :return: 없음
        """
        if logger_on:
            self._logger.info(f'[{node_name}] : delete_container 실행')

        container = self.find_container(container_name=container_name, node_name=node_name, logger_on=False)
        if container is not None:
            self._connections[node_name].zun_connection.containers.delete(id=container_name, force=True)

        timeout_count = 0
        if logger_on:
            self._logger.info(f'[{node_name}] : 컨테이너 삭제 대기 중')
        while container is not None or timeout_count <= timeout:
            container = self.find_container(container_name=container_name, node_name=node_name, logger_on=False)
            time.sleep(1)
            timeout_count += 1
