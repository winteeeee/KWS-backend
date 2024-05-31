from sqlalchemy import select, create_engine
from sqlalchemy.orm import Session

from model.db_models import Base, Node, Network, Flavor, NodeNetwork, NodeFlavor, Server, Container
from database.factories import MySQLEngineFactory
from config.config import node_config, openstack_config


def drop_tables():
    print('테이블 삭제')
    engine = MySQLEngineFactory().get_instance()
    Base.metadata.drop_all(engine)


def create_tables():
    print('테이블 생성')
    engine = MySQLEngineFactory().get_instance()
    Base.metadata.create_all(engine)


def insert_default_value():
    engine = MySQLEngineFactory()
    print('데이터베이스 초기화 작업 시작')

    with (Session(engine.get_instance()) as session, session.begin()):
        print('노드 컨픽 주입')
        for node in node_config['nodes']:
            if len(session.scalars(select(Node).where(Node.name == node['name'])).all()) == 0:
                session.add(Node(**node))

        print('기본 네트워크 주입')
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

        print('기본 플레이버 주입')
        for flavor in openstack_config['flavors']:
            if len(session.scalars(select(Flavor).where(Flavor.name == flavor['name'])).all()) == 0:
                session.add(Flavor(name=flavor['name'],
                                   vcpu=flavor['vcpu'],
                                   ram=flavor['ram'],
                                   disk=flavor['disk'],
                                   is_default=True))

        print('연관 관계 설정')
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


def db_migration(from_db_id: str,
                 from_db_passwd: str,
                 from_db_ip: str,
                 from_db_port: int,
                 from_db_name: str,
                 to_db_id: str,
                 to_db_passwd: str,
                 to_db_ip: str,
                 to_db_port: int,
                 to_db_name: str):
    print('데이터베이스 마이그레이션 시작')
    from_db_engine = create_engine(
        f"mysql+pymysql://{from_db_id}:{from_db_passwd}@{from_db_ip}"
        f":{from_db_port}/{from_db_name}"
    )
    to_db_engine = create_engine(
        f"mysql+pymysql://{to_db_id}:{to_db_passwd}@{to_db_ip}"
        f":{to_db_port}/{to_db_name}"
    )

    print('목표 데이터베이스 초기화 중')
    Base.metadata.drop_all(to_db_engine)
    Base.metadata.create_all(to_db_engine)

    print('기존 데이터베이스에서 인스턴스를 불러오는 중')
    with (Session(from_db_engine) as from_db_session, from_db_session.begin()):
        nodes = from_db_session.scalars(select(Node)).all()
        networks = from_db_session.scalars(select(Network)).all()
        flavors = from_db_session.scalars(select(Flavor)).all()
        node_networks = from_db_session.scalars(select(NodeNetwork)).all()
        node_flavors = from_db_session.scalars(select(NodeFlavor)).all()
        servers = from_db_session.scalars(select(Server)).all()
        containers = from_db_session.scalars(select(Container)).all()

        print('현재 데이터베이스에 인스턴스 삽입')
        with (Session(to_db_engine) as session, session.begin()):
            for node in nodes:
                node_dict = node.__dict__
                del node_dict['_sa_instance_state']
                session.add(Node(**node_dict))
            for network in networks:
                network_dict = network.__dict__
                del network_dict['_sa_instance_state']
                session.add(Network(**network_dict))
            for flavor in flavors:
                flavor_dict = flavor.__dict__
                del flavor_dict['_sa_instance_state']
                session.add(Flavor(**flavor_dict))
            for node_network in node_networks:
                node_network_dict = node_network.__dict__
                del node_network_dict['_sa_instance_state']
                session.add(NodeNetwork(**node_network_dict))
            for node_flavor in node_flavors:
                node_flavor_dict = node_flavor.__dict__
                del node_flavor_dict['_sa_instance_state']
                session.add(NodeFlavor(**node_flavor_dict))
            for server in servers:
                server_dict = server.__dict__
                del server_dict['_sa_instance_state']
                session.add(Server(**server_dict))
            for container in containers:
                container_dict = container.__dict__
                del container_dict['_sa_instance_state']
                session.add(Container(**container_dict))
            session.commit()
