from starlette import status
from tortoise.contrib.test import TestCase

from app.tests.health_apis.helpers import make_client, signup_and_login


class TestAttendanceApi(TestCase):
    async def test_check_in_grants_points(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="att1@example.com", phone_number="01090000001")
            headers = {"Authorization": f"Bearer {token}"}

            res = await client.post("/api/v1/attendance-checks", headers=headers)
            assert res.status_code == status.HTTP_201_CREATED
            body = res.json()
            assert body["streak_days"] == 1
            assert body["reward_point"] == 10
            assert body["bonus_point"] == 0
            assert len(body["transaction_ids"]) == 1

            # 잔액 확인
            txs = await client.get("/api/v1/points/transactions", headers=headers)
            assert txs.status_code == status.HTTP_200_OK
            assert txs.json()["balance"] == 10

    async def test_check_in_twice_same_day_conflict(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="att2@example.com", phone_number="01090000002")
            headers = {"Authorization": f"Bearer {token}"}

            first = await client.post("/api/v1/attendance-checks", headers=headers)
            assert first.status_code == status.HTTP_201_CREATED
            second = await client.post("/api/v1/attendance-checks", headers=headers)
            assert second.status_code == status.HTTP_409_CONFLICT

    async def test_month_lookup_after_check_in(self):
        from datetime import date

        async with make_client() as client:
            token = await signup_and_login(client, email="att3@example.com", phone_number="01090000003")
            headers = {"Authorization": f"Bearer {token}"}
            await client.post("/api/v1/attendance-checks", headers=headers)
            today = date.today()
            month_q = f"{today.year:04d}-{today.month:02d}"

            res = await client.get(f"/api/v1/attendance-checks?month={month_q}", headers=headers)
            assert res.status_code == status.HTTP_200_OK
            body = res.json()
            assert body["month"] == month_q
            assert len(body["checked_dates"]) == 1
            assert body["current_streak"] == 1
            assert body["next_bonus_at"] == 7
