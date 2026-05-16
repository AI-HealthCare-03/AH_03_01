from datetime import date

from starlette import status
from tortoise.contrib.test import TestCase

from app.tests.challenge_apis.helpers import future_range, make_client, signup_and_login


class TestChallengePetIntegration(TestCase):
    async def test_challenge_verification_grants_point_and_xp(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="pet_chl@example.com", phone_number="01010100001")
            headers = {"Authorization": f"Bearer {token}"}

            # 펫 생성
            await client.post("/api/v1/pets", headers=headers, json={"name": "멍이"})

            # 챌린지 생성
            start, end = future_range(7)
            challenge = await client.post(
                "/api/v1/challenges",
                headers=headers,
                json={
                    "title": "물 마시기",
                    "category": "WATER",
                    "goal_type": "COUNT",
                    "goal_value": 8,
                    "unit": "잔",
                    "verification_type": "CHECK",
                    "max_participants": 1,
                    "start_date": start,
                    "end_date": end,
                },
            )
            cid = challenge.json()["id"]

            # CHECK 인증 → APPROVED → 포인트 + XP 적립
            verify = await client.post(
                "/api/v1/challenge-verifications",
                headers=headers,
                json={
                    "challenge_id": cid,
                    "method": "CHECK",
                    "verified_date": date.today().isoformat(),
                    "checked": True,
                },
            )
            assert verify.status_code == status.HTTP_201_CREATED

            # 포인트 잔액 확인 (daily reward 50/70/100 중 하나)
            txs = await client.get("/api/v1/points/transactions", headers=headers)
            assert txs.status_code == status.HTTP_200_OK
            body = txs.json()
            assert body["balance"] in {50, 70, 100}
            assert len(body["transactions"]) == 1
            assert body["transactions"][0]["source"] == "CHALLENGE_DAILY"

            # 펫 XP 적립 확인 (인증 1회 = 50 XP)
            pet = await client.get("/api/v1/pets/me", headers=headers)
            assert pet.status_code == status.HTTP_200_OK
            assert pet.json()["current_xp"] == 50
            assert pet.json()["total_xp"] == 50
            assert pet.json()["level"] == 1

    async def test_pet_interaction_consumes_points(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="pet_iter@example.com", phone_number="01010100002")
            headers = {"Authorization": f"Bearer {token}"}
            await client.post("/api/v1/pets", headers=headers, json={"name": "멍이"})

            # 시드: PointTransaction 직접 EARN 100
            from app.models.pet import PointSource, PointTransaction, PointTransactionType

            me = (await client.get("/api/v1/users/me", headers=headers)).json()
            await PointTransaction.create(
                user_id=me["id"],
                type=PointTransactionType.EARN,
                amount=100,
                balance_after=100,
                source=PointSource.ETC,
                description="seed",
            )

            res = await client.post(
                "/api/v1/pets/me/interactions",
                headers=headers,
                json={"type": "FEED"},
            )
            assert res.status_code == status.HTTP_201_CREATED
            body = res.json()
            assert body["point_cost"] == 10
            assert body["xp_gained"] == 5

            txs = await client.get("/api/v1/points/transactions", headers=headers)
            assert txs.json()["balance"] == 90
