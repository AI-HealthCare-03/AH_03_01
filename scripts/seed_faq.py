"""FAQ 초기 데이터 삽입 스크립트.

실행 방법:
    docker cp scripts/seed_faq.py fastapi:/tmp/seed_faq.py
    docker exec -i fastapi uv run --no-sync python /tmp/seed_faq.py

이미 FAQ 데이터가 존재하면 삽입을 건너뜁니다 (멱등 실행 가능).
"""

import asyncio
import os

import asyncpg

DB_CONFIG = dict(
    host=os.getenv("DB_HOST", "postgres"),
    port=int(os.getenv("DB_PORT", "5432")),
    user=os.getenv("DB_USER", "ozcoding"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "ai_health"),
)

FAQS = [
    # 계정 (ACCOUNT)
    (
        "비밀번호를 잊어버렸어요. 어떻게 재설정하나요?",
        "로그인 화면에서 '비밀번호 찾기'를 누른 후 이메일(아이디)과 이름을 입력하면 이메일 계정 인증을 통해 새 비밀번호를 설정할 수 있습니다.",
        "ACCOUNT",
        1,
    ),
    (
        "닉네임은 어떻게 변경하나요?",
        "마이페이지 → 프로필 편집에서 닉네임을 변경할 수 있습니다. 중복되지 않는 닉네임으로만 변경이 가능합니다.",
        "ACCOUNT",
        2,
    ),
    (
        "회원 탈퇴는 어떻게 하나요?",
        "회원탈퇴 시 탈퇴 이유를 선택 또는 직접 작성할 수 있습니다. 탈퇴 후 개인정보는 30일간 보관 후 완전히 삭제되며, 재가입은 탈퇴 즉시 가능합니다.",
        "ACCOUNT",
        3,
    ),
    # 챌린지 (CHALLENGE)
    (
        "챌린지 인증이 거부됐어요. 왜 그런가요?",
        "인증 사진이 기준에 맞지 않을 경우 AI가 거부할 수 있습니다. 선명한 사진으로 다시 시도해 주세요.",
        "CHALLENGE",
        1,
    ),
    (
        "챌린지는 하루에 몇 번 인증할 수 있나요?",
        "챌린지별로 인증 횟수가 다릅니다. 챌린지 상세 페이지에서 인증 횟수와 주기를 확인해 주세요.",
        "CHALLENGE",
        2,
    ),
    (
        "챌린지 중도 포기가 가능한가요?",
        "챌린지 상세 페이지에서 중도 포기가 가능합니다. 포기 후에는 해당 챌린지 참여 기록이 종료됩니다.",
        "CHALLENGE",
        3,
    ),
    # 건강 데이터 (HEALTH_DATA)
    (
        "혈압/혈당 기록을 수정하고 싶어요.",
        "건강 기록 화면에서 해당 날짜의 기록을 탭하면 수정 및 삭제가 가능합니다.",
        "HEALTH_DATA",
        1,
    ),
    (
        "건강 리포트는 얼마나 자주 업데이트되나요?",
        "월간 리포트는 매월 누적된 건강 데이터를 요약하여 제공됩니다. 혈압/혈당 추이 그래프, 챌린지 수행 내역 등을 PDF로 다운로드할 수 있습니다.",
        "HEALTH_DATA",
        2,
    ),
    # 포인트·보상 (REWARD)
    (
        "포인트 내역은 어디서 확인하나요?",
        "마이페이지 → 포인트 내역에서 최대 1년치 적립 및 사용 내역을 확인할 수 있습니다.",
        "REWARD",
        1,
    ),
    (
        "상점에서 구매한 아이템을 환불할 수 있나요?",
        "포인트로 구매한 아이템은 환불이 불가합니다. 구매 전 신중하게 선택해 주세요.",
        "REWARD",
        2,
    ),
]


async def main() -> None:
    conn = await asyncpg.connect(**DB_CONFIG)
    existing = await conn.fetchval("SELECT COUNT(*) FROM support_faqs WHERE category = 'REWARD'")
    if existing > 0:
        print(f"이미 REWARD FAQ {existing}개가 존재합니다. 삽입을 건너뜁니다.")
        await conn.close()
        return

    await conn.executemany(
        'INSERT INTO support_faqs (question, answer, category, "order") VALUES ($1, $2, $3, $4)',
        FAQS,
    )
    await conn.close()
    print(f"완료 — FAQ {len(FAQS)}개 삽입")


if __name__ == "__main__":
    asyncio.run(main())
