from starlette import status
from tortoise.contrib.test import TestCase

from app.tests.challenge_apis.helpers import future_range, make_client, signup_and_login


class TestChallengeCrudApi(TestCase):
    async def test_create_personal_challenge(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="cper@example.com", phone_number="01030000001")
            headers = {"Authorization": f"Bearer {token}"}
            start, end = future_range(14)
            res = await client.post(
                "/api/v1/challenges",
                headers=headers,
                json={
                    "title": "매일 30분 걷기",
                    "category": "EXERCISE",
                    "sub_category": "WALKING",
                    "goal_type": "DURATION",
                    "goal_value": 30,
                    "unit": "min",
                    "verification_type": "CHECK",
                    "max_participants": 1,
                    "start_date": start,
                    "end_date": end,
                },
            )
            assert res.status_code == status.HTTP_201_CREATED
            body = res.json()
            assert body["scope"] == "PERSONAL"
            assert body["status"] == "ACTIVE"
            assert body.get("invite_code") in (None, "")

    async def test_create_group_challenge_issues_invite_code(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="cgrp@example.com", phone_number="01030000002")
            headers = {"Authorization": f"Bearer {token}"}
            start, end = future_range(7)
            res = await client.post(
                "/api/v1/challenges",
                headers=headers,
                json={
                    "title": "물 8잔 함께",
                    "category": "WATER",
                    "goal_type": "COUNT",
                    "goal_value": 8,
                    "unit": "잔",
                    "verification_type": "CHECK",
                    "max_participants": 3,
                    "goal_config": {"group_target_count": 30},
                    "start_date": start,
                    "end_date": end,
                },
            )
            assert res.status_code == status.HTTP_201_CREATED
            body = res.json()
            assert body["scope"] == "GROUP"
            assert body["status"] == "RECRUITING"
            assert body["invite_code"]
            assert len(body["invite_code"]) >= 4

    async def test_list_filters_by_status_and_keyword(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="clst@example.com", phone_number="01030000003")
            headers = {"Authorization": f"Bearer {token}"}
            start, end = future_range(7)
            await client.post(
                "/api/v1/challenges",
                headers=headers,
                json={
                    "title": "근력운동 시작",
                    "category": "EXERCISE",
                    "sub_category": "STRENGTH",
                    "goal_type": "COUNT",
                    "goal_value": 10,
                    "unit": "회",
                    "verification_type": "CHECK",
                    "max_participants": 1,
                    "start_date": start,
                    "end_date": end,
                },
            )
            await client.post(
                "/api/v1/challenges",
                headers=headers,
                json={
                    "title": "수면 7시간",
                    "category": "SLEEP",
                    "goal_type": "DURATION",
                    "goal_value": 7,
                    "unit": "h",
                    "verification_type": "CHECK",
                    "max_participants": 1,
                    "start_date": start,
                    "end_date": end,
                },
            )

            res = await client.get("/api/v1/challenges?keyword=근력", headers=headers)
            assert res.status_code == status.HTTP_200_OK
            assert res.json()["total_elements"] == 1
            assert res.json()["items"][0]["title"] == "근력운동 시작"

    async def test_update_and_delete_owned_challenge(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="cmod@example.com", phone_number="01030000004")
            headers = {"Authorization": f"Bearer {token}"}
            start, end = future_range(5)
            created = await client.post(
                "/api/v1/challenges",
                headers=headers,
                json={
                    "title": "초기 제목",
                    "category": "DIET",
                    "goal_type": "CHECK",
                    "verification_type": "CHECK",
                    "max_participants": 1,
                    "start_date": start,
                    "end_date": end,
                },
            )
            cid = created.json()["id"]

            patch = await client.patch(
                f"/api/v1/challenges/{cid}",
                headers=headers,
                json={"title": "수정된 제목"},
            )
            assert patch.status_code == status.HTTP_200_OK
            assert patch.json()["title"] == "수정된 제목"

            delete = await client.delete(f"/api/v1/challenges/{cid}", headers=headers)
            assert delete.status_code == status.HTTP_204_NO_CONTENT

            get_after = await client.get(f"/api/v1/challenges/{cid}", headers=headers)
            assert get_after.status_code == status.HTTP_404_NOT_FOUND

    async def test_non_owner_cannot_modify(self):
        async with make_client() as client:
            owner = await signup_and_login(client, email="cown@example.com", phone_number="01030000005")
            owner_h = {"Authorization": f"Bearer {owner}"}
            start, end = future_range(5)
            created = await client.post(
                "/api/v1/challenges",
                headers=owner_h,
                json={
                    "title": "잠금 챌린지",
                    "category": "MEDITATION",
                    "goal_type": "DURATION",
                    "goal_value": 10,
                    "unit": "min",
                    "verification_type": "CHECK",
                    "max_participants": 1,
                    "start_date": start,
                    "end_date": end,
                },
            )
            cid = created.json()["id"]

            other = await signup_and_login(client, email="cother@example.com", phone_number="01030000006", name="타인")
            other_h = {"Authorization": f"Bearer {other}"}
            res = await client.patch(f"/api/v1/challenges/{cid}", headers=other_h, json={"title": "탈취"})
            assert res.status_code == status.HTTP_403_FORBIDDEN
