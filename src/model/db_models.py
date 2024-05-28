import datetime
from sqlalchemy import Integer, String, Date, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Server(Base):
    __tablename__ = "server"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(String(45))
    server_name: Mapped[str] = mapped_column(String(45), unique=True)
    start_date: Mapped[datetime] = mapped_column(Date)
    end_date: Mapped[datetime] = mapped_column(Date)
    floating_ip: Mapped[str] = mapped_column(String(45))
    network_name: Mapped[int] = mapped_column(ForeignKey('network.name'))
    network: Mapped['Network'] = relationship(back_populates='servers')
    node_name: Mapped[int] = mapped_column(ForeignKey('node.name'))
    node: Mapped['Node'] = relationship(back_populates='servers')
    flavor_name: Mapped[int] = mapped_column(ForeignKey('flavor.name'))
    flavor: Mapped['Flavor'] = relationship(back_populates='servers')
    image_name: Mapped[str] = mapped_column(String(45))


class Node(Base):
    __tablename__ = "node"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(45), unique=True)
    vcpu: Mapped[int] = mapped_column(Integer)
    ram: Mapped[int] = mapped_column(Integer)
    disk: Mapped[int] = mapped_column(Integer)
    auth_url: Mapped[str] = mapped_column(String(45), unique=True)
    servers: Mapped[list['Server']] = relationship()
    containers: Mapped[list['Container']] = relationship()
    node_networks: Mapped[list['NodeNetwork']] = relationship()
    node_flavors: Mapped[list['NodeFlavor']] = relationship()


class Container(Base):
    __tablename__ = "container"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_name: Mapped[str] = mapped_column(String(45))
    container_name: Mapped[str] = mapped_column(String(45), unique=True)
    start_date: Mapped[datetime] = mapped_column(Date)
    end_date: Mapped[datetime] = mapped_column(Date)
    image_name: Mapped[str] = mapped_column(String(45))
    password: Mapped[str] = mapped_column(String(100))
    ip: Mapped[str] = mapped_column(String(45))
    port: Mapped[str] = mapped_column(String(45))
    network_name: Mapped[int] = mapped_column(ForeignKey('network.name'))
    network: Mapped['Network'] = relationship(back_populates='containers')
    node_name: Mapped[int] = mapped_column(ForeignKey('node.name'))
    node: Mapped['Node'] = relationship(back_populates='containers')


class Flavor(Base):
    __tablename__ = "flavor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(45), unique=True)
    vcpu: Mapped[int] = mapped_column(Integer)
    ram: Mapped[int] = mapped_column(Integer)
    disk: Mapped[int] = mapped_column(Integer)
    is_default: Mapped[bool] = mapped_column(Boolean)
    servers: Mapped[list['Server']] = relationship()
    node_flavors: Mapped[list['NodeFlavor']] = relationship()


class Network(Base):
    __tablename__ = "network"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(45), unique=True)
    cidr: Mapped[str] = mapped_column(String(45), unique=True)
    is_default: Mapped[bool] = mapped_column(Boolean)
    is_external: Mapped[bool] = mapped_column(Boolean)
    servers: Mapped[list['Server']] = relationship()
    containers: Mapped[list['Container']] = relationship()
    node_networks: Mapped[list['NodeNetwork']] = relationship()


class NodeNetwork(Base):
    __tablename__ = "node_network"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_name: Mapped[int] = mapped_column(ForeignKey('node.name'))
    node: Mapped['Node'] = relationship(back_populates='node_networks')
    network_name: Mapped[int] = mapped_column(ForeignKey('network.name'))
    network: Mapped['Network'] = relationship(back_populates='node_networks')


class NodeFlavor(Base):
    __tablename__ = 'node_flavor'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_name: Mapped[int] = mapped_column(ForeignKey('node.name'))
    node: Mapped['Node'] = relationship(back_populates='node_flavors')
    flavor_name: Mapped[int] = mapped_column(ForeignKey('flavor.name'))
    flavor: Mapped['Flavor'] = relationship(back_populates='node_flavors')
