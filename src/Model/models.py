from pydantic import BaseModel


class ServerInfo(BaseModel):
    server_name: str
    image_name: str
    flavor_name: str
    network_name: str
    keypair_name: str
