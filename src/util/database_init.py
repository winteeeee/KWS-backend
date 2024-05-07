from model.db_models import Base
from database.factories import MySQLEngineFactory


def create_tables():
    engine = MySQLEngineFactory().get_instance()
    Base.metadata.create_all(engine)

