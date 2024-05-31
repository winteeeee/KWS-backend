import uvicorn
import threading

from config.config import server_config
from backend.backend_server import app
from util.scheduler import run_scheduler
from util.database_init import create_tables, insert_default_value, db_migration

if __name__ == "__main__":
    create_tables()
    insert_default_value()
    # 첫 배포 시엔 insert_default_value()를 끄고 db_migration()을 실행
    # db_migration(new_db_id='',
    #              new_db_passwd='',
    #              new_db_ip='',
    #              new_db_port=3306,
    #              new_db_name='')

    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    uvicorn.run(app, host=server_config["backend"]["host"], port=server_config["backend"]["port"], access_log=False)
