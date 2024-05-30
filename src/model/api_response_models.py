import json
from datetime import datetime

from fastapi import Response


class ApiResponse(Response):
    def __init__(self, code: int, data: object):
        super().__init__(
            media_type="application/json",
            status_code=code,
            content=json.dumps(data, default=str)
        )


class ErrorResponse(Response):
    def __init__(self, code: int, message: str):
        super().__init__(
            status_code=code,
            content=json.dumps({"data": message}, default=str)
        )


class ServerRentalResponseDTO:
    def __init__(self, name: str, private_key: object):
        self.name = name
        self.private_key = private_key


class ImageListResponseDTO:
    def __init__(self, name: str):
        self.name = name


class FlavorListResponseDTO:
    def __init__(self, name: str, cpu: int, ram: int, disk: int):
        self.name = name
        self.cpu = cpu
        self.ram = ram
        self.disk = disk


class ServersResponseDTO:
    def __init__(self,
                 user_name: str,
                 server_name: str,
                 floating_ip: str,
                 start_date: datetime,
                 end_date: datetime,
                 network_name: str,
                 node_name: str,
                 flavor_name: str,
                 image_name: str):
        self.user_name = user_name
        self.server_name = server_name
        self.floating_ip = floating_ip
        self.start_date = start_date
        self.end_date = end_date
        self.network_name = network_name
        self.node_name = node_name
        self.flavor_name = flavor_name
        self.image_name = image_name


class ContainersResponseDTO:
    def __init__(self,
                 user_name: str,
                 container_name: str,
                 start_date: datetime,
                 end_date: datetime,
                 image_name: str,
                 ip: str,
                 port: str,
                 network_name: str,
                 node_name: str):
        self.user_name = user_name
        self.container_name = container_name
        self.start_date = start_date
        self.end_date = end_date
        self.image_name = image_name
        self.ip = ip
        self.port = port
        self.network_name = network_name
        self.node_name = node_name


class UsingResourceDTO:
    def __init__(self, count: int, vcpus: int, ram: float, disk: int):
        self.count = count
        self.vcpus = vcpus
        self.ram = ram
        self.disk = disk


class NodeUsingResourceDTO:
    def __init__(self, name: str, count: int, vcpus: int, ram: float, disk: int):
        self.name = name
        self.count = count
        self.vcpus = vcpus
        self.ram = ram
        self.disk = disk


class NodesSpecResponseDTO:
    def __init__(self, total_spec: dict, nodes_spec: list[dict]):
        self.total_spec = total_spec
        self.nodes_spec = nodes_spec


class NodeSpecDTO:
    def __init__(self, name: str, vcpu: int, ram: int, disk: int):
        self.name = name
        self.vcpu = vcpu
        self.ram = ram
        self.disk = disk


class ResourceResponseDTO:
    def __init__(self, limit_resources: dict, using_resources: dict):
        self.limit_resources = limit_resources
        self.using_resources = using_resources


class UsingResourcesResponseDTO:
    def __init__(self, total_resource: dict, nodes_resource: list[dict]):
        self.total_resources = total_resource
        self.nodes_resources = nodes_resource


class NetworkResponseDTO:
    def __init__(self, name: str, subnet_cidr: str, is_external: bool):
        self.name = name
        self.subnet_cidr = subnet_cidr
        self.is_external = is_external


class NodeResponseDTO:
    def __init__(self, name: str, vcpu: int, ram: int, disk: int):
        self.name = name
        self.vcpu = vcpu
        self.ram = ram
        self.disk = disk
