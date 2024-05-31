from util.database_init import drop_tables, create_tables, insert_default_value

"""
데이터베이스 초기화 작업을 수행합니다.
연결되는 데이터베이스는 db_config으로 지정된 데이터베이스입니다.

데이터베이스의 모든 테이블을 DROP 한 후 다시 테이블을 생성합니다.
이후 openstack_config으로 명시된 기본 값들을 INSERT합니다.

시스템을 처음 실행하거나 컨픽의 내용이 변경되었을 때 적용시키기 위해 사용합니다.

주의! 테이블을 DROP 시키기 때문에 기본값 이외의 정보가 DB에 저장되있을 때 
실행 시 해당 데이터가 유실됩니다. 
"""

if __name__ == '__main__':
    drop_tables()
    create_tables()
    insert_default_value()
