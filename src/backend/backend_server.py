from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware

from backend.server_router import server_router
from backend.container_router import container_router
from backend.network_router import network_router
from backend.image_router import image_router
from backend.flavor_router import flavor_router
from backend.node_router import node_router
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

backend_logger.info("서버 실행 시작")
app = FastAPI()
app.include_router(server_router)
app.include_router(container_router)
app.include_router(network_router)
app.include_router(image_router)
app.include_router(flavor_router)
app.include_router(node_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LoggingMiddleware)
