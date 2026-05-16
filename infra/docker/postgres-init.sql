-- PostgreSQL 컨테이너 최초 부팅 시 1회 실행 (docker-entrypoint-initdb.d).
-- POSTGRES_USER 와 동일한 이름의 maintenance DB 를 생성한다.
-- asyncpg 는 database 미지정 시 username 으로 fallback 하므로
-- tortoise testing(initializer) 이 새 DB 를 만들기 전 연결할 수 있어야 한다.
SELECT 'CREATE DATABASE "' || current_user || '" OWNER "' || current_user || '"'
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = current_user
)\gexec

-- 현재 DB(ai_health) 와 maintenance DB 에 vector 확장 설치
CREATE EXTENSION IF NOT EXISTS vector;

-- template1 에도 설치해서, 이후 새로 만들어지는 모든 DB(테스트용 임시 DB 포함)가
-- vector 확장을 자동 상속하도록 한다.
\c template1
CREATE EXTENSION IF NOT EXISTS vector;
