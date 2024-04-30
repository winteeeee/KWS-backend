from model.db_models import Base
from database.factories import EngineFactory

from sqlalchemy.orm import Session


class DAO:
    def __init__(self, engine_factory: EngineFactory):
        self._engine = engine_factory.get_instance()

    def create_table(self) -> None:
        Base.metadata.create_all(self._engine)

    def save(self, model: Base) -> None:
        with Session(self._engine) as session, session.begin():
            session.add(model)
            session.commit()

    def save_all(self, models: list[Base]) -> None:
        with Session(self._engine) as session, session.begin():
            session.add_all(models)
            session.commit()

    def delete(self, model: Base) -> None:
        with Session(self._engine) as session, session.begin():
            session.delete(model)
            session.commit()

    def delete_all(self, models: list[Base]) -> None:
        with Session(self._engine) as session, session.begin():
            for model in models:
                session.delete(model)
        session.commit()