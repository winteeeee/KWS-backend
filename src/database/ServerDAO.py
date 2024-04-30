from database.DAO import DAO
from model.db_models import Server

from sqlalchemy.orm import Session
from sqlalchemy import select, Sequence


class ServerDAO(DAO):
    def find_all(self) -> Sequence[Server]:
        with Session(self._engine) as session, session.begin():
            return session.scalars(select(Server)).all()

    def find_by_server_name(self, server_name: str) -> Server:
        with Session(self._engine) as session, session.begin():
            return session.scalars(
                select(Server)
                .where(Server.server_name == server_name)
            ).one()
