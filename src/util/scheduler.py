import schedule
import time
from datetime import datetime
from sqlalchemy.orm import Session

from database.factories import MySQLEngineFactory
from model.db_models import Server
from openStack.openstack_controller import OpenStackController

controller = OpenStackController()
db_connection = MySQLEngineFactory().get_instance()


def delete_expired_data():
    today = datetime.now().date()

    with Session(db_connection) as session, session.begin():
        expired_servers = session.query(Server).filter(Server.end_date < today).all()
        for server in expired_servers:
            session.delete(server)
            controller.delete_server(server.server_name)
        session.commit()


schedule.every().day.at("00:00").do(delete_expired_data)


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(3600)


if __name__ == "__main__":
    run_scheduler()
