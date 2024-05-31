from pydantic import BaseModel


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
    network_name: str | None
    subnet_cidr: str | None
    password: str | None
    cloud_init: str | None


class ContainerCreateRequestDTO(BaseModel):
    user_name: str
    container_name: str
    start_date: str
    end_date: str
    image_name: str
    password: str
    network_name: str | None
    subnet_cidr: str | None
    env: str | None
    cmd: str | None


class ContainerReturnRequestDTO(BaseModel):
    container_name: str
    password: str


class ContainerExtensionRequestDTO(BaseModel):
    container_name: str
    password: str
    end_date: str
