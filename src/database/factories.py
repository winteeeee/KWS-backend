from config.config import db_config

from abc import *
from sqlalchemy import create_engine, Engine


class EngineFactory(metaclass=ABCMeta):
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super().__new__(cls)
        return cls.instance

    @abstractmethod
    def get_instance(self) -> Engine:
        pass


class MySQLEngineFactory(EngineFactory):
    def __init__(self):
        self._engine = create_engine(
            f"mysql+pymysql://{db_config['id']}:{db_config['passwd']}@{db_config['ip']}"
            f":{db_config['port']}/{db_config['name']}"
        )

    def get_instance(self) -> Engine:
        return self._engine
