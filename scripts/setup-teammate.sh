#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# scripts/setup-teammate.sh
#
# feat/LangGraph 신규 합류자 환경 셋업 자동화.
# - 필수 도구 점검 (docker / uv)
# - .env 생성 / 심볼릭 링크
# - docker-compose 기동 (postgres / redis / mysql / fastapi / ai-worker)
# - pgvector 확장 + DB dump 복원
# - 호스트·컨테이너 의존성 동기화
# - 인덱싱 (이미 dump 에 적재되어 있으면 자동 skip)
#
# 멱등 (재실행 안전). 어디서 실패해도 같은 단계로 재시도 가능.
#
# 실행:
#   chmod +x scripts/setup-teammate.sh
#   ./scripts/setup-teammate.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

cd "$(dirname "$0")/.."

# ─── 컬러 출력 ─────────────────────────────────────────
B='\033[1m'; R='\033[0;31m'; G='\033[0;32m'; Y='\033[0;33m'; C='\033[0;36m'; N='\033[0m'
ok()   { echo -e "${G}✓${N} $*"; }
info() { echo -e "${C}ℹ${N} $*"; }
warn() { echo -e "${Y}⚠${N} $*"; }
err()  { echo -e "${R}✗${N} $*" >&2; }
step() { echo; echo -e "${B}── $* ──${N}"; }

# ─── 0. 사전 도구 점검 ─────────────────────────────────
step "0. 사전 점검"
command -v docker >/dev/null || { err "docker 미설치 — https://www.docker.com/products/docker-desktop/"; exit 1; }
command -v uv     >/dev/null || { err "uv 미설치 — https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }
docker info >/dev/null 2>&1 || { err "Docker 데몬 미실행 — Docker Desktop 켜고 재실행"; exit 1; }
ok "docker / uv / Docker 데몬 OK"

# RAG 문서 점검 (gitignore 로 빠지므로 Drive 에서 받아와야 함)
if [[ ! -d "RAG/final docs" ]]; then
  err "RAG/final docs/ 디렉토리 누락"
  echo "  팀 Drive 에서 5개 마크다운을 받아 RAG/final docs/ 에 복사 후 재실행:"
  echo "    KDA2025_section_documentation_요약.md"
  echo "    KSH2022_section_documentation_요약.md"
  echo "    KSOLA2022_section_documentation_요약.md"
  echo "    서비스_이용_가이드_20260522.md"
  echo "    CHALLENGE_CATALOG_documentation.md"
  exit 1
fi
ok "RAG/final docs/ 존재"

# DB dump 점검
if [[ ! -f infra/db/full_dump.sql ]]; then
  warn "infra/db/full_dump.sql 누락"
  echo "  팀 Drive 의 [DB dump] 폴더에서 받아 infra/db/full_dump.sql 로 복사 후 재실행."
  echo "  (없이도 진행 가능 — 빈 DB 에 마이그레이션 수동 적용 필요, 권장 안 함)"
  read -rp "  dump 없이 계속? [y/N]: " ans
  [[ "${ans:-N}" =~ ^[yY]$ ]] || exit 1
  HAS_DUMP=0
else
  ok "infra/db/full_dump.sql 발견 ($(du -h infra/db/full_dump.sql | cut -f1))"
  HAS_DUMP=1
fi

# ─── 1. .env 셋업 ──────────────────────────────────────
step "1. .env 셋업"
if [[ ! -f envs/.local.env ]]; then
  cp envs/example.local.env envs/.local.env
  ok "envs/.local.env 생성 (example 복사)"
  warn "필수 값 채워주세요:"
  echo "  - OPENAI_API_KEY (필수, 본인 sk-... 키)"
  echo "  - SECRET_KEY     (필수, 32자 이상 — \`openssl rand -hex 32\` 추천)"
  echo "  - DB_USER/DB_PASSWORD/DB_NAME (compose 디폴트 사용하면 그대로 OK)"
  read -rp "  편집 마치고 Enter (Ctrl-C 로 중단): "
fi
[[ -L .env || -f .env ]] || ln -sf envs/.local.env .env
ok "envs/.local.env 준비, .env 심볼릭 링크 확인"

# 필수 ENV 검증
# shellcheck disable=SC1091
set -a; source envs/.local.env; set +a
[[ -n "${OPENAI_API_KEY:-}" && "$OPENAI_API_KEY" != "sk-replace-me" ]] \
  || { err "OPENAI_API_KEY 미설정 — envs/.local.env 편집 후 재실행"; exit 1; }
[[ -n "${SECRET_KEY:-}" && "$SECRET_KEY" != "CHANGE_ME_TO_A_LONG_RANDOM_STRING" ]] \
  || { err "SECRET_KEY 미설정 — envs/.local.env 편집 후 재실행"; exit 1; }
[[ -n "${DB_USER:-}" && -n "${DB_PASSWORD:-}" && -n "${DB_NAME:-}" ]] \
  || { err "DB_USER/DB_PASSWORD/DB_NAME 누락"; exit 1; }
ok "필수 ENV 검증 통과"

# ─── 2. docker compose 기동 ────────────────────────────
step "2. docker compose 기동 (--build)"
docker compose up -d --build
info "postgres healthy 대기..."
for _ in {1..60}; do
  if docker exec postgres pg_isready -U "$DB_USER" >/dev/null 2>&1; then
    ok "postgres healthy"
    break
  fi
  sleep 1
done

# ─── 3. pgvector + DB dump 복원 ───────────────────────
step "3. pgvector 확장 + DB 복원"
docker exec postgres psql -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null
ok "vector extension 활성"

# 이미 schema 가 적재되어 있으면 skip (멱등)
TABLES_EXIST=$(docker exec postgres psql -U "$DB_USER" -d "$DB_NAME" -tAc \
  "SELECT to_regclass('rag_documents');" 2>/dev/null || echo "")

if [[ -n "$TABLES_EXIST" && "$TABLES_EXIST" != "" ]]; then
  ok "DB schema 이미 존재 (rag_documents 발견) — 복원 skip"
elif [[ "$HAS_DUMP" == "1" ]]; then
  info "infra/db/full_dump.sql 복원 중..."
  docker exec -i postgres psql -U "$DB_USER" -d "$DB_NAME" < infra/db/full_dump.sql > /tmp/setup_restore.log 2>&1 \
    || { err "복원 실패 — /tmp/setup_restore.log 확인"; exit 1; }
  ok "DB 복원 완료"
else
  warn "DB schema 없음 — dump 없이 진행. 마이그레이션은 별도 수동 적용 필요."
fi

# ─── 4. 호스트 의존성 동기화 ──────────────────────────
step "4. uv sync (host) --group app"
uv sync --group app >/dev/null 2>&1 || uv sync --group app
ok "호스트 .venv 동기화"

# ─── 5. 컨테이너 의존성 동기화 ────────────────────────
step "5. fastapi 컨테이너 의존성 동기화"
# fastapi 컨테이너는 빌드 시점 deps 만 갖고 있어, 호스트 pyproject 변경분을 cp+sync.
docker cp pyproject.toml fastapi:/app/pyproject.toml
docker cp uv.lock        fastapi:/app/uv.lock
docker exec fastapi sh -c "cd /app && uv sync --group app" >/dev/null 2>&1 || \
  docker exec fastapi sh -c "cd /app && uv sync --group app"
docker restart fastapi >/dev/null
info "fastapi 재시작 + reload 안정화 대기..."
sleep 6
ok "컨테이너 deps 동기화"

# ─── 6. RAG 인덱싱 ────────────────────────────────────
step "6. RAG 인덱싱 (이미 적재된 source 는 자동 skip)"
uv run python -m scripts.rag.index_documents
ok "인덱싱 완료"
warn "컨테이너의 BM25 인덱스는 부팅 시점 메모리에 적재되므로 재시작 필요:"
docker restart fastapi >/dev/null
sleep 4
ok "fastapi 재시작 — BM25 인덱스 갱신"

# ─── 7. 테스트 사용자 + CHAT_REPL_USER_* 안내 ─────────
step "7. 테스트 사용자 확인 + CHAT_REPL_USER_* 채우기"
USER_COUNT=$(docker exec postgres psql -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM users;" 2>/dev/null || echo "0")
if [[ "$USER_COUNT" -gt 0 ]]; then
  ok "users 테이블에 ${USER_COUNT}명 존재"
  echo
  docker exec postgres psql -U "$DB_USER" -d "$DB_NAME" -c \
    "SELECT u.id, u.email,
            (SELECT count(*) FROM health_records WHERE user_id=u.id AND is_deleted=false) AS records
     FROM users u ORDER BY records DESC, u.created_at LIMIT 5;"
  echo
  warn "위 UUID 중 적절한 사용자를 envs/.local.env 의 CHAT_REPL_USER_* 에 채우세요:"
  echo "    CHAT_REPL_USER_WITH_DATA=<데이터 많은 사용자 UUID>"
  echo "    CHAT_REPL_USER_PARTIAL=<일부 데이터 사용자 UUID>"
  echo "    CHAT_REPL_USER_NO_DATA=<데이터 없는 사용자 UUID>"
  echo "  ⚠ 라인 앞 '# ' 는 반드시 제거 (주석 처리되어 있으면 인식 안 됨)"
else
  warn "users 테이블이 비어 있음 — 회원가입 API 로 테스트 사용자 생성 필요:"
  echo "    curl -X POST http://localhost:8000/api/v1/auth/signup \\"
  echo "      -H 'Content-Type: application/json' \\"
  echo "      -d '{\"email\":\"test@example.com\",\"password\":\"Test1234!\",\"nickname\":\"테스트\",\"name\":\"테스트\",\"phone_number\":\"010-1234-5678\"}'"
fi

# ─── 완료 ──────────────────────────────────────────────
echo
echo -e "${G}${B}✅ 셋업 완료${N}"
echo
echo "다음 단계:"
echo "  1) envs/.local.env 의 CHAT_REPL_USER_* 채우기 (위 안내)"
echo "  2) REPL 검증: uv run python -m scripts.rag.chat_repl"
echo "  3) FastAPI E2E:"
echo "     curl http://localhost:8000/api/docs   # Swagger UI"
echo
echo "유용한 명령:"
echo "  docker logs fastapi --tail 30        # 서버 로그"
echo "  docker logs fastapi --tail 100 | grep -E 'node:|BM25'  # 그래프 timing"
echo "  uv run ruff check app/               # lint"
echo "  uv run mypy app/                     # type check"
