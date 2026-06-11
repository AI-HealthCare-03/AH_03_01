from __future__ import annotations

from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from app.models.community import QuizAttempt
from app.repositories.community_repository import QuizRepository
from app.services.rewards import RewardService

SEOUL = ZoneInfo("Asia/Seoul")
DAILY_LIMIT = 5


def _today() -> date:
    return datetime.now(SEOUL).date()


class HealthQuizService:
    def __init__(self) -> None:
        self.repo = QuizRepository()
        self.reward_service = RewardService()

    async def get_today_quiz(self, user_id: UUID) -> dict:
        quiz = await self.repo.get_quiz_by_date(_today())
        if not quiz:
            raise ValueError("no_quiz_today")
        attempt = await self.repo.get_attempt(user_id, quiz.id)
        return {"quiz": quiz, "already_answered": attempt is not None}

    async def answer_quiz(self, user_id: UUID, quiz_id: int, selected_option: str) -> dict:
        # 이미 답한 경우
        if await self.repo.get_attempt(user_id, quiz_id):
            raise ValueError("already_answered")

        # 일일 제한 확인
        today_start = datetime.combine(_today(), datetime.min.time()).replace(tzinfo=SEOUL)
        daily_count = await QuizAttempt.filter(user_id=user_id, attempted_at__gte=today_start).count()
        if daily_count >= DAILY_LIMIT:
            raise ValueError("daily_limit_exceeded")

        quiz = await self.repo.get_quiz_by_date(_today())
        if not quiz or quiz.id != quiz_id:
            raise ValueError("quiz_not_found")

        is_correct = selected_option == quiz.correct_option
        points_earned = 0
        if is_correct:
            result = await self.reward_service.grant_quiz_correct(user_id=user_id, quiz_id=quiz_id)
            points_earned = result.amount

        await self.repo.create_attempt(
            user_id=user_id,
            quiz_id=quiz_id,
            selected_option=selected_option,
            is_correct=is_correct,
            points_earned=points_earned,
        )
        return {
            "is_correct": is_correct,
            "correct_option": quiz.correct_option,
            "explanation": quiz.explanation,
            "points_earned": points_earned,
        }

    async def get_attempt_history(self, user_id: UUID, page: int, size: int) -> tuple:
        attempts, total = await self.repo.list_attempts(user_id, page, size)
        return attempts, total
