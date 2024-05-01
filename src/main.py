import uvicorn

from config.config import server_config
from backend.backend_server import app
from util.scheduler import run_scheduler

if __name__ == "__main__":
    run_scheduler()
    uvicorn.run(app, host=server_config["host"], port=server_config["port"])
