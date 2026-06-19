from starlette import status
from tortoise.contrib.test import TestCase

from app.models.challenge import (
    ChallengeCategory,
    ChallengeDifficulty,
    ChallengeTemplate,
    ExerciseSubType,
    GoalType,
    VerificationType,
)
from app.tests.health_apis.helpers import make_client, signup_and_login
from app.tests.health_apis.test_predictions_api import _FULL_MALE_PROFILE_PAYLOAD


class TestChallengeRecommendationsApi(TestCase):
    async def _seed_walking_template(self):
        await ChallengeTemplate.create(
            category=ChallengeCategory.EXERCISE,
            sub_category=ExerciseSubType.WALKING,
            title="추천 걷기 챌린지",
            description="고혈압 대응",
            goal_type=GoalType.DURATION,
            goal_value_options=[20, 30, 45],
            default_unit="min",
            verification_type=VerificationType.CHECK,
            difficulty=ChallengeDifficulty.LEVEL_1,
            is_active=True,
        )

    async def _seed_full_profile(self, client, headers):
        # 예측 게이트(완성도 100%) 통과를 위해 모델입력 필수 필드를 모두 채운다.
        await client.post(
            "/api/v1/health-records?recordType=profile",
            headers=headers,
            json=_FULL_MALE_PROFILE_PAYLOAD,
        )
        await client.post(
            "/api/v1/health-records",
            headers=headers,
            json={
                "record_type": "BLOOD_PRESSURE",
                "sub_type": "HOSPITAL",
                "primary_value": 150,
                "secondary_value": 95,
                "unit": "mmHg",
                "measured_at": "2026-05-10T08:00:00+09:00",
            },
        )

    async def test_recommendations_for_prediction(self):
        await self._seed_walking_template()
        async with make_client() as client:
            token = await signup_and_login(client, email="rec@example.com", phone_number="01060000001")
            headers = {"Authorization": f"Bearer {token}"}
            await self._seed_full_profile(client, headers)
            pred = await client.post("/api/v1/predictions?diseaseType=HYPERTENSION", headers=headers, json={})
            pid = pred.json()["id"]

            res = await client.get(
                f"/api/v1/challenge-recommendations?predictionId={pid}&limit=3",
                headers=headers,
            )
            assert res.status_code == status.HTTP_200_OK
            body = res.json()
            assert body["prediction_id"] == pid
            assert len(body["items"]) >= 1
            categories = [item["category"] for item in body["items"]]
            assert "EXERCISE" in categories

    async def test_other_users_prediction_blocked(self):
        async with make_client() as client:
            owner_token = await signup_and_login(client, email="rec_own@example.com", phone_number="01060000002")
            owner_h = {"Authorization": f"Bearer {owner_token}"}
            await self._seed_full_profile(client, owner_h)
            pred = await client.post("/api/v1/predictions?diseaseType=HYPERTENSION", headers=owner_h, json={})
            pid = pred.json()["id"]

            intruder_token = await signup_and_login(
                client, email="rec_int@example.com", phone_number="01060000003", name="침입"
            )
            res = await client.get(
                f"/api/v1/challenge-recommendations?predictionId={pid}",
                headers={"Authorization": f"Bearer {intruder_token}"},
            )
            assert res.status_code == status.HTTP_404_NOT_FOUND
