from pydantic import BaseModel


class ServerCreateRequestDTO(BaseModel):
    user_name: str
    server_name: str
    image_name: str
    flavor_name: str
    network_name: str
    password: str | None
    cloud_init: str | None
    start_date: str
    end_date: str
