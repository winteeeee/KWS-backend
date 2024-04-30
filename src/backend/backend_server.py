from fastapi import FastAPI

from backend.openstack_router import router

app = FastAPI()
app.include_router(router)
