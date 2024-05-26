from sqlalchemy import select
from sqlalchemy.orm import Session

from model.db_models import Base, Node, Network, Flavor, NodeNetwork, NodeFlavor
from database.factories import MySQLEngineFactory
from config.config import node_config
from util.logger import get_logger

backend_logger = get_logger(name='backend', log_level='INFO', save_path="./log/backend")


def create_tables():
    backend_logger.info('테이블 생성')
    engine = MySQLEngineFactory().get_instance()
    Base.metadata.create_all(engine)


def insert_default_value():
    engine = MySQLEngineFactory()
    backend_logger.info('데이터베이스 초기화 작업 시작')

    with (Session(engine.get_instance()) as session, session.begin()):
        backend_logger.info('노드 컨픽 주입')
        for node in node_config['nodes']:
            if session.scalars(select(Node).where(Node.name == node['name'])).one_or_none() is None:
                session.add(Node(**node))

        backend_logger.info('기본 네트워크 주입')
        if session.scalars(select(Network).where(Network.name == 'public')).one_or_none() is None:
            session.add(Network(name='public',
                                cidr='192.168.0.0/24',
                                is_default=True))
        if session.scalars(select(Network).where(Network.name == 'default')).one_or_none() is None:
            session.add(Network(name='default',
                                cidr='192.168.233.0/24',
                                is_default=True))

        backend_logger.info('기본 플레이버 주입')
        if session.scalars(select(Flavor).where(Flavor.name == 'kws_small')).one_or_none() is None:
            session.add(Flavor(name='kws_small',
                               vcpu=1,
                               ram=512,
                               disk=5,
                               is_default=True))
        if session.scalars(select(Flavor).where(Flavor.name == 'kws_medium')).one_or_none() is None:
            session.add(Flavor(name='kws_medium',
                               vcpu=1,
                               ram=1024,
                               disk=10,
                               is_default=True))
        if session.scalars(select(Flavor).where(Flavor.name == 'kws_large')).one_or_none() is None:
            session.add(Flavor(name='kws_large',
                               vcpu=2,
                               ram=2048,
                               disk=20,
                               is_default=True))

        backend_logger.info('연관 관계 설정')
        for node in node_config['nodes']:
            if len(session.scalars(select(NodeNetwork).where(NodeNetwork.node_name == node['name'])).all()) == 0:
                session.add(NodeNetwork(node_name=node['name'],
                                        network_name='public'))
                session.add(NodeNetwork(node_name=node['name'],
                                        network_name='default'))
            if len(session.scalars(select(NodeFlavor).where(NodeFlavor.node_name == node['name'])).all()) == 0:
                session.add(NodeFlavor(node_name=node['name'],
                                       flavor_name='kws_small'))
                session.add(NodeFlavor(node_name=node['name'],
                                       flavor_name='kws_medium'))
                session.add(NodeFlavor(node_name=node['name'],
                                       flavor_name='kws_large'))

        session.commit()
