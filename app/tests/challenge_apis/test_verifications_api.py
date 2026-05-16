from datetime import date

from starlette import status
from tortoise.contrib.test import TestCase

from app.tests.challenge_apis.helpers import future_range, make_client, signup_and_login


class TestChallengeVerificationsApi(TestCase):
    async def _create_personal_check(self, client, headers, title="체크 챌린지"):
        start, end = future_range(7)
        res = await client.post(
            "/api/v1/challenges",
            headers=headers,
            json={
                "title": title,
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
        return res.json()

    async def test_create_check_verification_auto_approved(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="vchk@example.com", phone_number="01050000001")
            headers = {"Authorization": f"Bearer {token}"}
            challenge = await self._create_personal_check(client, headers)

            res = await client.post(
                "/api/v1/challenge-verifications",
                headers=headers,
                json={
                    "challenge_id": challenge["id"],
                    "method": "CHECK",
                    "verified_date": date.today().isoformat(),
                    "checked": True,
                },
            )
            assert res.status_code == status.HTTP_201_CREATED
            assert res.json()["status"] == "APPROVED"

    async def test_create_verification_outside_period_fails(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="vout@example.com", phone_number="01050000002")
            headers = {"Authorization": f"Bearer {token}"}
            challenge = await self._create_personal_check(client, headers)

            res = await client.post(
                "/api/v1/challenge-verifications",
                headers=headers,
                json={
                    "challenge_id": challenge["id"],
                    "method": "CHECK",
                    "verified_date": "2020-01-01",
                    "checked": True,
                },
            )
            assert res.status_code == status.HTTP_400_BAD_REQUEST

    async def test_photo_verification_remains_pending(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="vpho@example.com", phone_number="01050000003")
            headers = {"Authorization": f"Bearer {token}"}
            start, end = future_range(7)
            challenge = await client.post(
                "/api/v1/challenges",
                headers=headers,
                json={
                    "title": "사진 챌린지",
                    "category": "DIET",
                    "goal_type": "CHECK",
                    "verification_type": "PHOTO",
                    "max_participants": 1,
                    "start_date": start,
                    "end_date": end,
                },
            )
            cid = challenge.json()["id"]

            res = await client.post(
                "/api/v1/challenge-verifications",
                headers=headers,
                json={
                    "challenge_id": cid,
                    "method": "PHOTO",
                    "verified_date": date.today().isoformat(),
                    "photo_file_id": 12345,
                },
            )
            assert res.status_code == status.HTTP_201_CREATED
            assert res.json()["status"] == "PENDING"

    async def test_method_mismatch_rejected(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="vmis@example.com", phone_number="01050000004")
            headers = {"Authorization": f"Bearer {token}"}
            challenge = await self._create_personal_check(client, headers)

            res = await client.post(
                "/api/v1/challenge-verifications",
                headers=headers,
                json={
                    "challenge_id": challenge["id"],
                    "method": "PHOTO",
                    "verified_date": date.today().isoformat(),
                    "photo_file_id": 999,
                },
            )
            assert res.status_code == status.HTTP_400_BAD_REQUEST

    async def test_reaction_like_increments_count(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="vrea@example.com", phone_number="01050000005")
            headers = {"Authorization": f"Bearer {token}"}
            challenge = await self._create_personal_check(client, headers)
            verification = await client.post(
                "/api/v1/challenge-verifications",
                headers=headers,
                json={
                    "challenge_id": challenge["id"],
                    "method": "CHECK",
                    "verified_date": date.today().isoformat(),
                    "checked": True,
                },
            )
            vid = verification.json()["id"]

            like = await client.post(
                f"/api/v1/challenge-verifications/{vid}/reactions",
                headers=headers,
                json={"type": "LIKE"},
            )
            assert like.status_code == status.HTTP_201_CREATED

            comment = await client.post(
                f"/api/v1/challenge-verifications/{vid}/reactions",
                headers=headers,
                json={"type": "COMMENT", "content": "잘하셨네요!"},
            )
            assert comment.status_code == status.HTTP_201_CREATED

            listed = await client.get(
                f"/api/v1/challenge-verifications/{vid}/reactions",
                headers=headers,
            )
            body = listed.json()
            assert body["like_count"] == 1
            assert len(body["comments"]) == 1
            assert body["comments"][0]["content"] == "잘하셨네요!"

    async def test_summary_endpoint(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="vsum@example.com", phone_number="01050000006")
            headers = {"Authorization": f"Bearer {token}"}
            challenge = await self._create_personal_check(client, headers)
            for offset in range(3):
                d = date.today()
                await client.post(
                    "/api/v1/challenge-verifications",
                    headers=headers,
                    json={
                        "challenge_id": challenge["id"],
                        "method": "CHECK",
                        "verified_date": d.isoformat(),
                        "checked": True,
                    },
                )
                if offset == 0:
                    break  # 동일 일자 unique constraint 회피

            res = await client.get("/api/v1/challenge-summaries?period=weekly", headers=headers)
            assert res.status_code == status.HTTP_200_OK
            body = res.json()
            assert body["total"] >= 1
            assert body["success_count"] >= 1
