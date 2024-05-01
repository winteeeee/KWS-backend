import uvicorn
import threading

from config.config import server_config
from backend.backend_server import app
from util.scheduler import run_scheduler

if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    uvicorn.run(app, host=server_config["host"], port=server_config["port"])
