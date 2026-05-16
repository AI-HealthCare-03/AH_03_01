set -eo pipefail

COLOR_GREEN=$(tput setaf 2)
COLOR_BLUE=$(tput setaf 4)
COLOR_RED=$(tput setaf 1)
COLOR_NC=$(tput sgr0)

cd "$(dirname "$0")/../.."

source .env

echo "${COLOR_BLUE}Find Tests${COLOR_NC}"

HAS_TESTS=false
POSTGRES_CONTAINER_NAME=postgres

if [ -d "./app/tests" ] && find ./app/tests -name 'test_*.py' -print -quit | read ; then
  HAS_TESTS=true
fi

echo "Has tests: $HAS_TESTS"

if [ "$HAS_TESTS" = true ]; then
  if docker ps --format '{{.Names}}' | grep -q "^${POSTGRES_CONTAINER_NAME}$"; then
    echo "${COLOR_BLUE}→ Postgres container found. Preparing test database...${COLOR_NC}"

    # 두 가지를 보장해야 한다.
    # 1) tortoise testing 의 maintenance 연결(with_db=False)이 fallback 하는
    #    username 동일 DB 가 존재할 것.
    # 2) tortoise testing 이 매번 새로 만드는 임시 DB(test_xxxxxxxx)에도
    #    vector 확장이 있어야 하므로, template1 에 vector 를 설치해 둔다.
    docker exec -i ${POSTGRES_CONTAINER_NAME} \
      psql -U ${DB_USER} -d ${DB_NAME} -v ON_ERROR_STOP=0 <<EOF
SELECT 'CREATE DATABASE "${DB_USER}" OWNER "${DB_USER}"'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_USER}')\gexec
\connect template1
CREATE EXTENSION IF NOT EXISTS vector;
\connect ${DB_NAME}
DROP DATABASE IF EXISTS test;
CREATE DATABASE test OWNER ${DB_USER};
\connect test
CREATE EXTENSION IF NOT EXISTS vector;
EOF

    echo "${COLOR_BLUE}Run Pytest with Coverage${COLOR_NC}"

    if ! uv run coverage run -m pytest app; then
      echo ""
      echo "${COLOR_RED}✖ Pytest failed.${COLOR_NC}"
      echo "${COLOR_RED}→ Fix the test failures above and re-run.${COLOR_NC}"
      exit 1
    fi

    echo "${COLOR_BLUE}Coverage Report${COLOR_NC}"
    if ! uv run coverage report -m ; then
      echo "${COLOR_RED}✖ Coverage check failed.${COLOR_NC}"
      exit 1
    fi
  else
    echo "${COLOR_RED} Postgres Docker Container Not Found. Run docker compose up postgres.${COLOR_NC}"
  fi
else
  echo "${COLOR_BLUE}No tests found. Skipping tests.${COLOR_NC}"
fi
