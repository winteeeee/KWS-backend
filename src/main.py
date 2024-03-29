import uvicorn

from Config.config import server_config
from BackEnd.backend_server import app

if __name__ == "__main__":
    uvicorn.run(app, host=server_config["host"], port=server_config["port"])
