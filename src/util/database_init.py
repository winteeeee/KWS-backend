from sqlalchemy import select
from sqlalchemy.orm import Session

from model.db_models import Base, Node
from database.factories import MySQLEngineFactory
from config.config import node_config


def create_tables():
    engine = MySQLEngineFactory().get_instance()
    Base.metadata.create_all(engine)


def insert_node_config():
    engine = MySQLEngineFactory()
    with (Session(engine.get_instance()) as session, session.begin()):
        if session.scalars(select(Node).where(Node.name == node_config['controller']['name'])).one_or_none() is None:
            session.add(Node(**node_config['controller']))

        for compute in node_config['compute']:
            if session.scalars(select(Node).where(Node.name == compute['name'])).one_or_none() is None:
                session.add(Node(**compute))

        session.commit()
