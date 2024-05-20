from fastapi import APIRouter

container_router = APIRouter(prefix="/container")


@container_router.post("/rental")
def rental():
    # TODO 구현
    pass


@container_router.delete("/return")
def container_return():
    # TODO 구현
    pass
