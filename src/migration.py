from util.database_init import db_migration

if __name__ == "__main__":
    db_migration(old_db_id='',
                 old_db_passwd='',
                 old_db_ip='',
                 old_db_port=3306,
                 old_db_name='')