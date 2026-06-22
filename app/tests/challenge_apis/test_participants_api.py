from starlette import status
from tortoise.contrib.test import TestCase

from app.tests.challenge_apis.helpers import future_range, make_client, signup_and_login


class TestChallengeParticipantsApi(TestCase):
    async def _create_group(self, client, headers, max_participants=3):
        start, end = future_range(7)
        return await client.post(
            "/api/v1/challenges",
            headers=headers,
            json={
                "title": "그룹 챌린지",
                "category": "EXERCISE",
                "sub_category": "WALKING",
                "goal_type": "COUNT",
                "goal_value": 10,
                "unit": "회",
                "verification_type": "CHECK",
                "max_participants": max_participants,
                "goal_config": {"group_target_count": 30},
                "start_date": start,
                "end_date": end,
            },
        )

    async def test_join_by_code_auto_approved(self):
        # 유효한 초대 코드 보유 = 신뢰로 간주 → 코드 참가는 즉시 APPROVED (방장 승인 불필요).
        async with make_client() as client:
            owner = await signup_and_login(client, email="own_app@example.com", phone_number="01040000001")
            owner_h = {"Authorization": f"Bearer {owner}"}
            created = await self._create_group(client, owner_h)
            cid = created.json()["id"]
            invite_code = created.json()["invite_code"]

            member = await signup_and_login(
                client, email="mem_app@example.com", phone_number="01040000002", name="멤버"
            )
            member_h = {"Authorization": f"Bearer {member}"}
            join = await client.post(
                f"/api/v1/challenges/{cid}/participants?action=join",
                headers=member_h,
                json={"invite_code": invite_code},
            )
            assert join.status_code == status.HTTP_201_CREATED
            assert join.json()["status"] == "APPROVED"

            # 즉시 승인 상태이므로 멤버는 바로 챌린지 상세에 접근 가능
            ok = await client.get(f"/api/v1/challenges/{cid}", headers=member_h)
            assert ok.status_code == status.HTTP_200_OK

    async def test_invalid_invite_code(self):
        async with make_client() as client:
            owner = await signup_and_login(client, email="own_bad@example.com", phone_number="01040000003")
            owner_h = {"Authorization": f"Bearer {owner}"}
            created = await self._create_group(client, owner_h)
            cid = created.json()["id"]

            member = await signup_and_login(
                client, email="mem_bad@example.com", phone_number="01040000004", name="멤버"
            )
            member_h = {"Authorization": f"Bearer {member}"}
            res = await client.post(
                f"/api/v1/challenges/{cid}/participants?action=join",
                headers=member_h,
                json={"invite_code": "WRONGCD"},
            )
            assert res.status_code == status.HTTP_404_NOT_FOUND

    async def test_leave_challenge_member_ok_owner_forbidden(self):
        async with make_client() as client:
            owner = await signup_and_login(client, email="own_lv@example.com", phone_number="01040000005")
            owner_h = {"Authorization": f"Bearer {owner}"}
            created = await self._create_group(client, owner_h)
            cid = created.json()["id"]
            invite_code = created.json()["invite_code"]

            member = await signup_and_login(client, email="mem_lv@example.com", phone_number="01040000006", name="멤버")
            member_h = {"Authorization": f"Bearer {member}"}
            join = await client.post(
                f"/api/v1/challenges/{cid}/participants?action=join",
                headers=member_h,
                json={"invite_code": invite_code},
            )
            member_user_id = join.json()["user_id"]
            await client.patch(
                f"/api/v1/challenges/{cid}/participants/{member_user_id}?action=approve",
                headers=owner_h,
            )

            leave = await client.delete(f"/api/v1/challenges/{cid}/participants", headers=member_h)
            assert leave.status_code == status.HTTP_204_NO_CONTENT

            owner_leave = await client.delete(f"/api/v1/challenges/{cid}/participants", headers=owner_h)
            assert owner_leave.status_code == status.HTTP_400_BAD_REQUEST
