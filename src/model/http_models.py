from pydantic import BaseModel


class ServerDTOForCreate(BaseModel):
    user_name: str
    server_name: str
    image_name: str
    flavor_name: str
    network_name: str
    password: str | None
    cloud_init: str | None
    start_date: str
    end_date: str


class ServerDTOForUpdate(BaseModel):
    server_name: str
    host_ip: str
    password: str
    end_date: str


class ServerDTOForDelete(BaseModel):
    server_name: str
    host_ip: str
    password: str
