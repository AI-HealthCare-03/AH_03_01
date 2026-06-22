from __future__ import annotations

from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from app.models.community import QuizAttempt
from app.repositories.community_repository import DailyAssignmentRepository, QuizRepository
from app.services.rewards import RewardService

SEOUL = ZoneInfo("Asia/Seoul")
DAILY_LIMIT = 5


def _today() -> date:
    return datetime.now(SEOUL).date()


class HealthQuizService:
    def __init__(self) -> None:
        self.repo = QuizRepository()
        self.reward_service = RewardService()

    async def get_available_quizzes(self, user_id: UUID) -> list:
        today = _today()
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=SEOUL)
        assignment_repo = DailyAssignmentRepository()

        assignments = await assignment_repo.get_today_assignments(user_id, today)

        if not assignments:
            # 동시 첫 요청(같은 사용자)이 각자 빈 결과를 보고 서로 다른 랜덤 셋을 배정하면 하루 목표치를
            # 초과 배정한다 → 사용자별 PG advisory xact lock 으로 직렬화하고 락 안에서 재확인(double-check).
            async with in_transaction() as conn:
                await conn.execute_query(
                    "SELECT pg_advisory_xact_lock(hashtext($1))",
                    [f"quiz_assign:{user_id}:{today.isoformat()}"],
                )
                assignments = await assignment_repo.get_today_assignments(user_id, today)
                if not assignments:
                    # 오늘 이미 답한 수를 제외한 나머지 슬롯만 배정
                    today_answered_count = await QuizAttempt.filter(
                        user_id=user_id, attempted_at__gte=today_start
                    ).count()
                    remaining_slots = DAILY_LIMIT - today_answered_count
                    candidates = (
                        await self.repo.list_unanswered_quizzes(user_id, remaining_slots) if remaining_slots > 0 else []
                    )
                    if candidates:
                        await assignment_repo.create_assignments(user_id, [q.id for q in candidates], today)
                        assignments = await assignment_repo.get_today_assignments(user_id, today)

        if not assignments:
            return []

        # 오늘 배정된 퀴즈 중 오늘 이미 푼 것만 제외 (재출제 대응: 전체 기간 아닌 오늘 기준)
        answered_today_ids = set(
            await QuizAttempt.filter(
                user_id=user_id,
                quiz_id__in=[a.quiz_id for a in assignments],
                attempted_at__gte=today_start,
            ).values_list("quiz_id", flat=True)
        )
        return [a.quiz for a in assignments if a.quiz_id not in answered_today_ids]

    async def get_today_quiz(self, user_id: UUID) -> dict:
        quizzes = await self.get_available_quizzes(user_id)
        if not quizzes:
            raise ValueError("no_quiz_today")
        return {"quiz": quizzes[0], "already_answered": False}

    async def answer_quiz(self, user_id: UUID, quiz_id: int, selected_option: str) -> dict:
        today = _today()
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=SEOUL)
        if await self.repo.get_today_attempt(user_id, quiz_id, today_start):
            raise ValueError("already_answered")

        quiz = await self.repo.get_quiz_by_id(quiz_id)
        if not quiz:
            raise ValueError("quiz_not_found")

        is_correct = selected_option == quiz.correct_option
        points_earned = 0
        try:
            async with in_transaction() as conn:
                # daily_count 를 트랜잭션 밖에서 읽으면 서로 다른 퀴즈를 동시에 답할 때 둘 다 한도 검사를
                # 통과해 DAILY_LIMIT 을 초과 저장할 수 있다(TOCTOU). 사용자별 advisory xact lock 으로
                # 직렬화하고 락 안에서 한도를 재확인한다(퀴즈 배정 get_available_quizzes 와 동일 패턴).
                await conn.execute_query(
                    "SELECT pg_advisory_xact_lock(hashtext($1))",
                    [f"quiz_answer:{user_id}:{today.isoformat()}"],
                )
                daily_count = await QuizAttempt.filter(user_id=user_id, attempted_at__gte=today_start).count()
                if daily_count >= DAILY_LIMIT:
                    raise ValueError("daily_limit_exceeded")
                if is_correct:
                    result = await self.reward_service.grant_quiz_correct(user_id=user_id, quiz_id=quiz_id)
                    points_earned = result.amount

                await self.repo.create_attempt(
                    user_id=user_id,
                    quiz_id=quiz_id,
                    selected_option=selected_option,
                    is_correct=is_correct,
                    points_earned=points_earned,
                    attempted_date=today,
                )
        except IntegrityError:
            raise ValueError("already_answered") from None
        return {
            "is_correct": is_correct,
            "correct_option": quiz.correct_option,
            "explanation": quiz.explanation,
            "points_earned": points_earned,
        }

    async def get_attempt_history(self, user_id: UUID, page: int, size: int) -> tuple:
        attempts, total = await self.repo.list_attempts(user_id, page, size)
        return attempts, total
