# infra/db/ — DB dump 공유 디렉토리

본 디렉토리에 들어가는 `*.sql` / `*.dump` / `*.tar` / `*.backup` 파일은 **모두 git-ignored**.
DB dump 는 **PHI(사용자 이메일·해시 비번·health 측정값·위험도 결과 등)를 포함**할 수 있어
공개 저장소에 절대 올리지 않는다. 팀 공유는 **사내 Google Drive 등 비공개 채널만 사용**.

## 산출물

- **`full_dump.sql`** — `pg_dump --no-owner --no-privileges` 결과. schema + 모든 data.
  - 신규 합류자가 `scripts/setup-teammate.sh` 로 한 번에 복원하는 베이스라인.
  - 사용자/health/rag_documents/challenge 등 PHI 포함.

## 새 dump 생성 (관리자)

```bash
# 호스트에서 (docker-compose 가 띄운 postgres 사용)
DBU=$(grep -E '^DB_USER=' envs/.local.env | cut -d= -f2)
DBN=$(grep -E '^DB_NAME=' envs/.local.env | cut -d= -f2)
docker exec postgres pg_dump -U "$DBU" -d "$DBN" \
  --no-owner --no-privileges \
  > infra/db/full_dump.sql
```

생성 후 사내 Drive 의 `[프로젝트] DB dump` 폴더에 업로드.
파일명 규칙: `full_dump_YYYYMMDD.sql` 같이 날짜 suffix 권장.

## 복원 (팀원)

`scripts/setup-teammate.sh` 가 자동 처리하지만, 수동 절차는:

```bash
# 1) 컨테이너 기동 후 빈 DB 준비
docker compose up -d postgres
DBU=$(grep -E '^DB_USER=' envs/.local.env | cut -d= -f2)
DBN=$(grep -E '^DB_NAME=' envs/.local.env | cut -d= -f2)
docker exec postgres psql -U "$DBU" -d "$DBN" -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 2) Drive 에서 받은 full_dump.sql 을 infra/db/ 에 복사 후 import
docker exec -i postgres psql -U "$DBU" -d "$DBN" < infra/db/full_dump.sql
```

## 보안 / 폐기 정책

- dump 는 Drive 의 **접근 제한 폴더** 에만 (전체 공유 링크 금지).
- 사용자 탈퇴·PHI 삭제 요청 발생 시 기존 dump 는 폐기하고 새 dump 재생성.
- 로컬에 받아둔 dump 는 사용 후 삭제 권장.
