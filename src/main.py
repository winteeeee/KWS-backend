import uvicorn
import threading

from config.config import server_config
from backend.backend_server import app
from util.scheduler import run_scheduler

"""
서버의 엔트리포인트입니다.
데이터베이스 초기화 및 컨픽 작성 이후 실행시키세요.
"""

if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    uvicorn.run(app, host=server_config["backend"]["host"], port=server_config["backend"]["port"], access_log=False)
