from starlette import status
from tortoise.contrib.test import TestCase

from app.tests.health_apis.helpers import make_client, signup_and_login

# 모델입력 필수 필드(MALE 기준 24개) 전부 채운 페이로드.
_FULL_MALE_PROFILE_PAYLOAD = {
    "height_cm": 170,
    "weight_kg": 78,
    "waist_cm": 92,
    "systolic_bp": 120,
    "diastolic_bp": 80,
    "fasting_blood_sugar": 95,
    "sleep_weekday": 7,
    "sleep_weekend": 8,
    "moderate_exercise_hour": 1,
    "smoking_risk": 1,
    "current_smoker": 1,
    "mid_act_day": 3,
    "walk_day": 5,
    "water_count": 6,
    "family_dm": 1,
    "family_hp": 1,
    "family_hl": 0,
    "alcohol_freq_y": 2,
    "alcohol_cup": 3,
    "fruit_freq": 5,
    "veg_freq_1": 5,
    "out_meal_freq": 3,
    "breakfast_freq": 7,
    "anemia": 0,
}
# 여성 한정 필수 2개.
_FEMALE_ONLY_FIELDS = {
    "is_menopause": 0,
    "ocp_total_months": 12,
}


class TestProfileCompletenessApi(TestCase):
    async def _get_profile(self, client, headers) -> dict:
        res = await client.get("/api/v1/health-records?recordType=profile", headers=headers)
        assert res.status_code == status.HTTP_200_OK, res.json()
        return res.json()

    async def test_completeness_full_male(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="comp_full@example.com", phone_number="01033330001")
            headers = {"Authorization": f"Bearer {token}"}
            await client.post(
                "/api/v1/health-records?recordType=profile",
                headers=headers,
                json=_FULL_MALE_PROFILE_PAYLOAD,
            )
            body = await self._get_profile(client, headers)
            comp = body["completeness"]
            assert comp["total"] == 24
            assert comp["filled"] == 24
            assert comp["percent"] == 100
            assert comp["missing_fields"] == []
            assert comp["complete"] is True

    async def test_completeness_partial_male(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="comp_partial@example.com", phone_number="01033330002")
            headers = {"Authorization": f"Bearer {token}"}
            # 24개 중 4개만 채움 → 20개 누락.
            await client.post(
                "/api/v1/health-records?recordType=profile",
                headers=headers,
                json={"height_cm": 170, "weight_kg": 78, "waist_cm": 92, "systolic_bp": 120},
            )
            body = await self._get_profile(client, headers)
            comp = body["completeness"]
            assert comp["total"] == 24
            assert comp["filled"] == 4
            assert comp["percent"] == round(4 / 24 * 100)  # 17
            assert comp["complete"] is False
            assert set(comp["missing_fields"]) >= {"diastolic_bp", "fasting_blood_sugar", "anemia"}
            # 이미 채운 필드는 누락 목록에 없어야 함.
            assert "height_cm" not in comp["missing_fields"]

    async def test_completeness_empty_profile(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="comp_empty@example.com", phone_number="01033330003")
            headers = {"Authorization": f"Bearer {token}"}
            # 프로필 미입력 상태 — get_or_init 으로 빈 프로필이 생성되며 전부 미충족.
            body = await self._get_profile(client, headers)
            comp = body["completeness"]
            assert comp["total"] == 24
            assert comp["filled"] == 0
            assert comp["percent"] == 0
            assert comp["complete"] is False
            assert len(comp["missing_fields"]) == 24

    async def test_completeness_female_includes_extra_fields(self):
        async with make_client() as client:
            token = await signup_and_login(
                client, email="comp_female@example.com", phone_number="01033330004", gender="FEMALE"
            )
            headers = {"Authorization": f"Bearer {token}"}
            # 여성은 is_menopause/ocp_total_months 가 필수 → 24개만 채우면 2개 누락.
            await client.post(
                "/api/v1/health-records?recordType=profile",
                headers=headers,
                json=_FULL_MALE_PROFILE_PAYLOAD,
            )
            body = await self._get_profile(client, headers)
            comp = body["completeness"]
            assert comp["total"] == 26
            assert comp["filled"] == 24
            assert comp["complete"] is False
            assert set(comp["missing_fields"]) == {"is_menopause", "ocp_total_months"}

            # 여성 한정 2개까지 채우면 100% 완성.
            await client.post(
                "/api/v1/health-records?recordType=profile",
                headers=headers,
                json=_FEMALE_ONLY_FIELDS,
            )
            body2 = await self._get_profile(client, headers)
            comp2 = body2["completeness"]
            assert comp2["total"] == 26
            assert comp2["filled"] == 26
            assert comp2["percent"] == 100
            assert comp2["complete"] is True
            assert comp2["missing_fields"] == []

    async def test_completeness_male_excludes_female_fields(self):
        async with make_client() as client:
            token = await signup_and_login(
                client, email="comp_male_excl@example.com", phone_number="01033330005", gender="MALE"
            )
            headers = {"Authorization": f"Bearer {token}"}
            await client.post(
                "/api/v1/health-records?recordType=profile",
                headers=headers,
                json=_FULL_MALE_PROFILE_PAYLOAD,
            )
            body = await self._get_profile(client, headers)
            comp = body["completeness"]
            # 남성은 여성 한정 필드가 total/missing 어디에도 들어가지 않음.
            assert comp["total"] == 24
            assert "is_menopause" not in comp["missing_fields"]
            assert "ocp_total_months" not in comp["missing_fields"]
            assert comp["complete"] is True


class TestPredictionGate(TestCase):
    async def test_prediction_blocked_when_incomplete(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="gate_block@example.com", phone_number="01033330006")
            headers = {"Authorization": f"Bearer {token}"}
            # 일부만 입력 → 게이트 422.
            await client.post(
                "/api/v1/health-records?recordType=profile",
                headers=headers,
                json={"height_cm": 170, "weight_kg": 78},
            )
            res = await client.post("/api/v1/predictions?diseaseType=HYPERTENSION", headers=headers, json={})
            assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            detail = res.json()["detail"]
            assert detail["message"]
            assert isinstance(detail["missing_fields"], list)
            assert len(detail["missing_fields"]) > 0
            assert "systolic_bp" in detail["missing_fields"]

    async def test_prediction_blocked_when_no_profile(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="gate_noprofile@example.com", phone_number="01033330007")
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.post("/api/v1/predictions?diseaseType=DIABETES", headers=headers, json={})
            assert res.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            detail = res.json()["detail"]
            assert len(detail["missing_fields"]) == 24

    async def test_prediction_allowed_when_complete(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="gate_pass@example.com", phone_number="01033330008")
            headers = {"Authorization": f"Bearer {token}"}
            await client.post(
                "/api/v1/health-records?recordType=profile",
                headers=headers,
                json=_FULL_MALE_PROFILE_PAYLOAD,
            )
            res = await client.post("/api/v1/predictions?diseaseType=HYPERTENSION", headers=headers, json={})
            assert res.status_code == status.HTTP_201_CREATED
            assert res.json()["disease_type"] == "HYPERTENSION"
