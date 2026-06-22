"""ChatRAGGraph 검증 도구 — REPL(별도 터미널) + 단발(Claude Code 안에서 ! 명령) 듀얼 모드.

기능:
- 사용자 선택 (데이터 있음/없음/부분) 으로 시나리오 전환
- 질문 입력 → run_chat_rag 1회 실행 → 응답 + 소요시간 + 메타데이터 출력
- 출처 청크 미리보기 (source/section/title)
- 인터랙티브 REPL: 'user N' 으로 활성 사용자 전환, 'exit'/Ctrl-D 로 종료

실행 방식 ① REPL (별도 터미널 필수 — 인터랙티브 stdin):
    uv run python -m scripts.rag.chat_repl

실행 방식 ② 단발 (Claude Code 의 ! 접두어로 호출 가능):
    uv run python -m scripts.rag.chat_repl -u 1 -q "내 BMI 적정한가요?"
    uv run python -m scripts.rag.chat_repl -u 3 -q "내 혈압이 정상인가요?"

실행 방식 ③ 배치 (질문 여러 개 일괄):
    uv run python -m scripts.rag.chat_repl -u 1 -q "Q1?" -q "Q2?" -q "Q3?"
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from uuid import UUID

from tortoise import Tortoise

# 노드별 timing 로그(app.graphs.chat_rag_graph 의 _timed_node) 가 stdout 에 보이도록 설정.
logging.basicConfig(
    level=logging.INFO,
    format="  · %(message)s",
)
# 다른 라이브러리(httpx/openai) 의 INFO 노이즈는 억제 — 그래프 로그만 보고 싶음.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("tortoise").setLevel(logging.WARNING)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _bootstrap_env_from_dotenv() -> None:
    """envs/.local.env (또는 .env 심볼릭) 의 환경변수를 os.environ 에 inject.

    pydantic-settings(app.core.config.Config) 는 app 설정만 자동 로드하므로,
    검증 도구 ENV 키(CHAT_REPL_USER_*) 도 동일 파일에서 읽기 위해 부트스트랩.
    이미 셸에 있는 값은 덮어쓰지 않는다.
    """
    candidates = [
        PROJECT_ROOT / ".env",  # 루트 symlink (envs/.local.env 가리킴)
        PROJECT_ROOT / "envs" / ".local.env",
    ]
    for env_path in candidates:
        if not env_path.exists():
            continue
        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
            return  # 첫 번째 발견된 파일만 사용
        except OSError:
            continue


# os.environ.get() 으로 ENV 를 읽기 전에 부트스트랩. import 순서 중요 — 아래
# app.core.db.databases / chat_rag_graph 의 config 임포트는 영향 받지 않으나,
# 본 도구 자체의 CHAT_REPL_USER_* 조회는 이 호출에 의존.
_bootstrap_env_from_dotenv()

from app.core.db.databases import TORTOISE_ORM  # noqa: E402 — _bootstrap_env 이후
from app.graphs.chat_rag_graph import run_chat_rag  # noqa: E402


def _load_user(env_key: str, label: str) -> tuple[str, UUID] | None:
    """ENV 에서 테스트용 사용자 UUID 를 읽는다. 비어 있으면 None.

    개발/검증 도구에 실제 사용자 식별자를 코드에 박는 걸 피하기 위해 ENV 로 분리.
    `envs/.local.env` 에 `CHAT_REPL_USER_WITH_DATA=<uuid>` 식으로 설정.
    """
    raw = os.environ.get(env_key, "").strip()
    if not raw:
        return None
    try:
        return (label, UUID(raw))
    except ValueError:
        print(f"  ⚠️  {env_key} 값이 UUID 형식이 아님: {raw[:8]}...", file=sys.stderr)
        return None


# 사용자 키 → (라벨, UUID). 미설정 항목은 자동 제외.
_RAW_USERS = {
    "1": _load_user("CHAT_REPL_USER_WITH_DATA", "with-data"),
    "2": _load_user("CHAT_REPL_USER_PARTIAL", "partial"),
    "3": _load_user("CHAT_REPL_USER_NO_DATA", "no-data"),
}
USERS: dict[str, tuple[str, UUID]] = {k: v for k, v in _RAW_USERS.items() if v is not None}

HELP = """
명령:
  user 1|2|3   — 활성 사용자 전환
  help         — 이 도움말
  exit | quit  — 종료
  (그 외 입력) — 챗봇에 질문
"""


def print_result(elapsed: float, r, question: str | None = None) -> None:  # noqa: ANN001 — REPL 인쇄용
    if question is not None:
        print(f"\nQ: {question}")
    print(
        f"[{elapsed:.2f}s] intent={r.intent} | needs_health_data={r.needs_health_data} "
        f"| is_fallback={r.is_fallback} | rev={r.eval_revision_count} | conf={r.confidence:.2f}"
    )
    if r.missing_fields:
        print(f"  missing_fields: {r.missing_fields}")
    if r.action_hint:
        print(f"  action_hint: {r.action_hint}")
    if r.disclaimer:
        print(f"  disclaimer: {r.disclaimer}")
    if r.sources:
        print(f"  sources ({len(r.sources)}):")
        for i, c in enumerate(r.sources[:5], 1):
            sec = c.metadata.get("section_id", "?") if hasattr(c, "metadata") else "?"
            title = (c.title or "")[:60]
            print(f"    {i}. {c.source} / {sec} — {title}")
    print("\n┌─ ANSWER ───────────────────────────────────────────────────────────┐")
    print(r.answer)
    print("└────────────────────────────────────────────────────────────────────┘")


async def _run_one(question: str, user_key: str) -> None:
    uid = USERS[user_key][1]
    t0 = time.time()
    r = await run_chat_rag(question=question, user_id=uid, thread_id=f"repl-{user_key}")
    print_result(time.time() - t0, r, question=question)


async def main_oneshot(questions: list[str], user_key: str) -> None:
    """단발/배치 모드 — 인자로 받은 질문(들)을 순서대로 실행하고 종료."""
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        print(f"활성 사용자: {user_key} — {USERS[user_key][0]}")
        for q in questions:
            await _run_one(q, user_key)
    finally:
        await Tortoise.close_connections()


async def main_repl() -> None:
    """인터랙티브 REPL 모드 — 별도 터미널에서 실행 권장."""
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        print("=" * 70)
        print("  ChatRAGGraph REPL")
        print("=" * 70)
        print("사용자:")
        for k, (label, _uid) in USERS.items():
            print(f"  {k}: {label}")
        print(HELP)

        current_key = next(iter(USERS))
        print(f"활성 사용자: {current_key} — {USERS[current_key][0]}")

        while True:
            try:
                line = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n종료.")
                break
            if not line:
                continue
            if line in {"exit", "quit"}:
                break
            if line == "help":
                print(HELP)
                continue
            if line.startswith("user "):
                key = line.split(maxsplit=1)[1].strip()
                if key in USERS:
                    current_key = key
                    print(f"  → 전환: {USERS[key][0]}")
                else:
                    print(f"  ? 알 수 없는 사용자. 가능: {list(USERS)}")
                continue

            try:
                await _run_one(line, current_key)
            except Exception as e:  # noqa: BLE001 — REPL 이므로 예외도 가시화
                print(f"  ⚠️  실행 실패: {type(e).__name__}: {e}")
    finally:
        await Tortoise.close_connections()


def parse_args() -> argparse.Namespace:
    if not USERS:
        print(
            "  ❌ 테스트 사용자가 설정되지 않았습니다. envs/.local.env 에 아래 중 하나 이상 추가하세요:\n"
            "     CHAT_REPL_USER_WITH_DATA=<uuid>\n"
            "     CHAT_REPL_USER_PARTIAL=<uuid>\n"
            "     CHAT_REPL_USER_NO_DATA=<uuid>",
            file=sys.stderr,
        )
        raise SystemExit(2)

    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    default_user = next(iter(USERS))
    p.add_argument(
        "-u",
        "--user",
        default=default_user,
        choices=list(USERS),
        help="활성 사용자 키. CHAT_REPL_USER_* ENV 로 설정된 사용자만 선택 가능.",
    )
    p.add_argument(
        "-q",
        "--question",
        action="append",
        help="단발/배치 실행할 질문. 여러 번 지정 시 순차 실행. 생략하면 인터랙티브 REPL.",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.question:
        asyncio.run(main_oneshot(questions=args.question, user_key=args.user))
    else:
        asyncio.run(main_repl())
