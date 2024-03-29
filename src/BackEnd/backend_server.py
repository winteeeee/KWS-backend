from fastapi import FastAPI

from BackEnd.openstack_router import router

app = FastAPI()
app.include_router(router)
