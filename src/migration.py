from util.database_init import db_migration

"""
데이터베이스 마이그레이션 작업을 수행합니다.
from_db에서 to_db로 데이터를 복사합니다.

DB 컨테이너를 내부 네트워크에 연결시킬 경우 DB 관련 조작이 어려울 수 있어
마이그레이션을 통해 해결합니다.

from_db에서 원하는 값으로 업데이트한 후 to_db로 마이그레이션 하세요.

기본적으로 mysql 사용을 전제하여 구현되었습니다.
다른 DB 사용 시 engine 연결 코드 수정이 필요합니다.
"""

if __name__ == "__main__":
    db_migration(from_db_id='',
                 from_db_passwd='',
                 from_db_ip='',
                 from_db_port=3306,
                 from_db_name='',
                 to_db_id='',
                 to_db_passwd='',
                 to_db_ip='',
                 to_db_port=3306,
                 to_db_name='')
