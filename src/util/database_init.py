from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from model.db_models import Base, Node, Network, Flavor, NodeNetwork, NodeFlavor, Server, Container
from database.factories import MySQLEngineFactory
from config.config import node_config, openstack_config
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
            if len(session.scalars(select(Node).where(Node.name == node['name'])).all()) == 0:
                session.add(Node(**node))

        backend_logger.info('기본 네트워크 주입')
        if len(session.scalars(select(Network).where(Network.name == openstack_config['external_network']['name'])).all()) == 0:
            session.add(Network(name=openstack_config['external_network']['name'],
                                cidr=openstack_config['external_network']['cidr'],
                                is_default=True,
                                is_external=True))
        if len(session.scalars(select(Network).where(Network.name == openstack_config['internal_network']['name'])).all()) == 0:
            session.add(Network(name=openstack_config['internal_network']['name'],
                                cidr=openstack_config['internal_network']['cidr'],
                                is_default=True,
                                is_external=False))

        backend_logger.info('기본 플레이버 주입')
        for flavor in openstack_config['flavors']:
            if len(session.scalars(select(Flavor).where(Flavor.name == flavor['name'])).all()) == 0:
                session.add(Flavor(name=flavor['name'],
                                   vcpu=flavor['vcpu'],
                                   ram=flavor['ram'],
                                   disk=flavor['disk'],
                                   is_default=True))

        backend_logger.info('연관 관계 설정')
        for node in node_config['nodes']:
            if len(session.scalars(select(NodeNetwork).where(NodeNetwork.node_name == node['name'])).all()) == 0:
                session.add(NodeNetwork(node_name=node['name'],
                                        network_name=openstack_config['external_network']['name']))
                session.add(NodeNetwork(node_name=node['name'],
                                        network_name=openstack_config['internal_network']['name']))
            if len(session.scalars(select(NodeFlavor).where(NodeFlavor.node_name == node['name'])).all()) == 0:
                for flavor in openstack_config['flavors']:
                    session.add(NodeFlavor(node_name=node['name'],
                                           flavor_name=flavor['name']))
        session.commit()


def db_migration(old_db_id: str,
                 old_db_passwd: str,
                 old_db_ip: str,
                 old_db_port: int,
                 old_db_name: str):
    backend_logger.info('데이터베이스 마이그레이션 시작')
    engine = MySQLEngineFactory()
    old_db_engine = create_engine(
        f"mysql+pymysql://{old_db_id}:{old_db_passwd}@{old_db_ip}"
        f":{old_db_port}/{old_db_name}"
    )

    backend_logger.info('기존 데이터베이스에서 인스턴스를 불러오는 중')
    with (Session(old_db_engine) as old_db_session, old_db_session.begin()):
        nodes = old_db_session.scalars(select(Node)).all()
        networks = old_db_session.scalars(select(Network)).all()
        flavors = old_db_session.scalars(select(Flavor)).all()
        node_networks = old_db_session.scalars(select(NodeNetwork)).all()
        node_flavors = old_db_session.scalars(select(NodeFlavor)).all()
        servers = old_db_session.scalars(select(Server)).all()
        containers = old_db_session.scalars(select(Container)).all()

        backend_logger.info('현재 데이터베이스에 인스턴스 삽입')
        with (Session(engine.get_instance()) as session, session.begin()):
            for node in nodes:
                session.add(node)
            for network in networks:
                session.add(network)
            for flavor in flavors:
                session.add(flavor)
            for node_network in node_networks:
                session.add(node_network)
            for node_flavor in node_flavors:
                session.add(node_flavor)
            for server in servers:
                session.add(server)
            for container in containers:
                session.add(container)
            session.commit()
