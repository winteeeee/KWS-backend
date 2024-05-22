from sqlalchemy import select
from sqlalchemy.orm import Session

from model.db_models import Base, Node
from database.factories import MySQLEngineFactory
from config.config import node_config
from util.logger import get_logger

backend_logger = get_logger(name='backend', log_level='INFO', save_path="./log/backend")


def create_tables():
    backend_logger.info('테이블 생성')
    engine = MySQLEngineFactory().get_instance()
    Base.metadata.create_all(engine)


def insert_node_config():
    engine = MySQLEngineFactory()
    backend_logger.info('노드 컨픽 주입')
    with (Session(engine.get_instance()) as session, session.begin()):
        if session.scalars(select(Node).where(Node.name == node_config['controller']['name'])).one_or_none() is None:
            session.add(Node(**node_config['controller']))

        for compute in node_config['compute']:
            if session.scalars(select(Node).where(Node.name == compute['name'])).one_or_none() is None:
                session.add(Node(**compute))

        session.commit()
