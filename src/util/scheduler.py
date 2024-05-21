import schedule
import time
from datetime import datetime
from sqlalchemy.orm import Session

from database.factories import MySQLEngineFactory
from model.db_models import Server, Container
from openStack.openstack_controller import OpenStackController

controller = OpenStackController()
db_connection = MySQLEngineFactory().get_instance()


def delete_expired_data():
    today = datetime.now().date()

    with Session(db_connection) as session, session.begin():
        expired_servers = session.query(Server).filter(Server.end_date < today).all()
        expired_containers = session.query(Container).filter(Container.end_date < today).all()

        for server in expired_servers:
            session.delete(server)
            controller.delete_server(server.server_name)

        for container in expired_containers:
            session.delete(container)
            controller.delete_container(container.container_name)

        session.commit()


schedule.every().day.at("00:00").do(delete_expired_data)


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    run_scheduler()
