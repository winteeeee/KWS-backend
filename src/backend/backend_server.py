from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware

from backend.openstack_router import openstack_router
from backend.db_router import db_router
from backend.container_router import container_router
from config.config import server_config
from util.logger import get_logger

backend_logger = get_logger(name='backend', log_level='INFO', save_path="./log/backend")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        backend_logger.info(f"{request.client.host}:{request.client.port} - \"{request.method} {request.url.path} HTTP/{request.scope['http_version']}\" {response.status_code}")
        return response


origins = [
    "http://localhost:3000",
    f"http://{server_config['frontend']['host']}:{server_config['frontend']['port']}"
]

app = FastAPI()
app.include_router(openstack_router)
app.include_router(db_router)
app.include_router(container_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)



