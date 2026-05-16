"""챌린지·출석·퀴즈 등에서 발생하는 보상을 PointTransaction 로 적립한다.

펫 도메인이 추가되면서 본 모듈은 더 이상 로깅 스텁이 아니다. 실제 적립 + 펫 XP 가산을
원자적으로 수행한다. (XP 가산은 호출 측에서 명시적으로 PetService 를 호출하도록 분리해
의존 사이클을 만들지 않는다.)
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from tortoise.transactions import in_transaction

from app.models.pet import PointSource, PointTransaction
from app.repositories.pet_repository import PointTransactionRepository


@dataclass(slots=True)
class RewardResult:
    transaction: PointTransaction
    amount: int
    source: PointSource
    reward_type: str
    description: str


class RewardService:
    DAILY_OPTIONS = (50, 70, 100)
    PERIOD_REWARD = 200
    GROUP_TABLE = {
        "LEVEL_1": 100,
        "LEVEL_2": 150,
        "LEVEL_3": 200,
        "LEVEL_4": 250,
    }
    WEEKLY_RANKING = (500, 300, 100)
    ATTENDANCE_DAILY = 10
    ATTENDANCE_BONUS_THRESHOLDS = (7, 14, 30)
    ATTENDANCE_BONUS_AMOUNT = 20
    QUIZ_CORRECT = 50

    def __init__(self) -> None:
        self.point_repo = PointTransactionRepository()

    async def grant_daily(self, *, user_id: int, challenge_id: int, verification_id: int) -> RewardResult:
        amount = random.choice(self.DAILY_OPTIONS)
        tx = await self.point_repo.grant(
            user_id=user_id,
            amount=amount,
            source=PointSource.CHALLENGE_DAILY,
            source_id=verification_id,
            description=f"챌린지 {challenge_id} 일일 인증 보상",
        )
        return RewardResult(
            transaction=tx,
            amount=amount,
            source=PointSource.CHALLENGE_DAILY,
            reward_type="daily",
            description=tx.description or "",
        )

    async def grant_period_completion(self, *, user_id: int, challenge_id: int) -> RewardResult:
        amount = self.PERIOD_REWARD
        tx = await self.point_repo.grant(
            user_id=user_id,
            amount=amount,
            source=PointSource.CHALLENGE_PERIOD,
            source_id=challenge_id,
            description=f"챌린지 {challenge_id} 기간 달성 보상",
        )
        return RewardResult(
            transaction=tx,
            amount=amount,
            source=PointSource.CHALLENGE_PERIOD,
            reward_type="period",
            description=tx.description or "",
        )

    async def grant_group_completion(
        self,
        *,
        user_id: int,
        challenge_id: int,
        difficulty_level: str,
    ) -> RewardResult:
        amount = self.GROUP_TABLE.get(difficulty_level, 0)
        if amount <= 0:
            raise ValueError(f"알 수 없는 그룹 난이도: {difficulty_level}")
        tx = await self.point_repo.grant(
            user_id=user_id,
            amount=amount,
            source=PointSource.CHALLENGE_GROUP,
            source_id=challenge_id,
            description=f"챌린지 {challenge_id} 그룹 난이도 {difficulty_level} 달성 보상",
        )
        return RewardResult(
            transaction=tx,
            amount=amount,
            source=PointSource.CHALLENGE_GROUP,
            reward_type="group",
            description=tx.description or "",
        )

    async def grant_attendance_daily(self, *, user_id: int, attendance_id: int) -> RewardResult:
        amount = self.ATTENDANCE_DAILY
        tx = await self.point_repo.grant(
            user_id=user_id,
            amount=amount,
            source=PointSource.ATTENDANCE_DAILY,
            source_id=attendance_id,
            description="출석 보상",
        )
        return RewardResult(
            transaction=tx,
            amount=amount,
            source=PointSource.ATTENDANCE_DAILY,
            reward_type="attendance",
            description=tx.description or "",
        )

    async def grant_attendance_bonus(
        self,
        *,
        user_id: int,
        attendance_id: int,
        streak_days: int,
    ) -> RewardResult:
        amount = self.ATTENDANCE_BONUS_AMOUNT
        tx = await self.point_repo.grant(
            user_id=user_id,
            amount=amount,
            source=PointSource.ATTENDANCE_BONUS,
            source_id=attendance_id,
            description=f"연속 출석 {streak_days}일 보너스",
        )
        return RewardResult(
            transaction=tx,
            amount=amount,
            source=PointSource.ATTENDANCE_BONUS,
            reward_type="attendance_bonus",
            description=tx.description or "",
        )

    async def grant_quiz_correct(self, *, user_id: int, quiz_id: int) -> RewardResult:
        amount = self.QUIZ_CORRECT
        tx = await self.point_repo.grant(
            user_id=user_id,
            amount=amount,
            source=PointSource.QUIZ,
            source_id=quiz_id,
            description="건강 퀴즈 정답 보상",
        )
        return RewardResult(
            transaction=tx, amount=amount, source=PointSource.QUIZ, reward_type="quiz", description=tx.description or ""
        )

    async def grant(
        self,
        *,
        user_id: int,
        amount: int,
        source: PointSource,
        source_id: int | None = None,
        description: str | None = None,
    ) -> PointTransaction:
        return await self.point_repo.grant(
            user_id=user_id,
            amount=amount,
            source=source,
            source_id=source_id,
            description=description,
        )

    async def spend(
        self,
        *,
        user_id: int,
        amount: int,
        source: PointSource,
        source_id: int | None = None,
        description: str | None = None,
    ) -> PointTransaction:
        return await self.point_repo.spend(
            user_id=user_id,
            amount=amount,
            source=source,
            source_id=source_id,
            description=description,
        )

    async def with_transaction(self, callback: Any) -> Any:
        async with in_transaction():
            return await callback()
