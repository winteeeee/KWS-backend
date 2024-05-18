import uvicorn
import threading

from config.config import server_config
from backend.backend_server import app
from util.scheduler import run_scheduler
from util.database_init import create_tables, insert_node_config

if __name__ == "__main__":
    create_tables()
    insert_node_config()

    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    uvicorn.run(app, host=server_config["backend"]["host"], port=server_config["backend"]["port"], access_log=False)
