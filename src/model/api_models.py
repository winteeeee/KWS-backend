import json
from datetime import datetime

from pydantic import BaseModel
from fastapi import Response


class ServerCreateRequestDTO(BaseModel):
    user_name: str
    server_name: str
    start_date: str
    end_date: str
    image_name: str
    flavor_name: str
    vcpus: int | None
    ram: int | None
    disk: int | None
    network_name: str
    password: str | None
    cloud_init: str | None
    node_name: str


class ApiResponse(Response):
    def __init__(self, code: int, data: object):
        super().__init__(
            media_type="application/json",
            status_code=code,
            content=json.dumps(data, default=str)
        )


class ErrorResponse(Response):
    def __init__(self, code:int, message: str):
        super().__init__(
            status_code=code,
            content=message
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


class ResourceDTO:
    def __init__(self, count: int, vcpus: int, ram: float, disk: int):
        self.count = count
        self.vcpus = vcpus
        self.ram = ram
        self.disk = disk


class NodeResourceDTO:
    def __init__(self, name: str, count: int, vcpus: int, ram: float, disk: int):
        self.name = name
        self.count = count
        self.vcpus = vcpus
        self.ram = ram
        self.disk = disk


class ResourcesResponseDTO:
    def __init__(self, total_resource: dict, nodes_resource: list[dict]):
        self.total_resources = total_resource
        self.nodes_resources = nodes_resource
