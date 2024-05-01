from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.openstack_router import router

origins = [
    "http://localhost:3000"
]

app = FastAPI()
app.include_router(router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
