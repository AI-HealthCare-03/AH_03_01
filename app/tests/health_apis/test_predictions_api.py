from starlette import status
from tortoise.contrib.test import TestCase

from app.tests.health_apis.helpers import make_client, signup_and_login


class TestPredictionsApi(TestCase):
    async def _seed_profile_and_bp(self, client, headers, systolic: int, diastolic: int) -> None:
        await client.post(
            "/api/v1/health-records?recordType=profile",
            headers=headers,
            json={
                "height_cm": 170,
                "weight_kg": 78,
                "waist_cm": 92,
                "current_smoker": 1,
                "alcohol_freq_y": 2,
                "family_hp": 1,
                "family_dm": 1,
            },
        )
        await client.post(
            "/api/v1/health-records",
            headers=headers,
            json={
                "record_type": "BLOOD_PRESSURE",
                "sub_type": "HOSPITAL",
                "primary_value": systolic,
                "secondary_value": diastolic,
                "unit": "mmHg",
                "measured_at": "2026-05-10T08:00:00+09:00",
            },
        )

    async def test_create_hypertension_prediction_high_risk(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="hyp@example.com", phone_number="01022220001")
            headers = {"Authorization": f"Bearer {token}"}
            await self._seed_profile_and_bp(client, headers, 150, 95)

            res = await client.post("/api/v1/predictions?diseaseType=HYPERTENSION", headers=headers, json={})
            assert res.status_code == status.HTTP_201_CREATED
            body = res.json()
            assert body["disease_type"] == "HYPERTENSION"
            assert body["risk_level"] in {"RISK", "HIGH_RISK"}
            assert float(body["risk_score"]) > 0
            assert len(body["contributing_factors"]) >= 1

    async def test_create_diabetes_prediction_with_snapshot_override(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="dia@example.com", phone_number="01022220002")
            headers = {"Authorization": f"Bearer {token}"}
            await self._seed_profile_and_bp(client, headers, 118, 78)

            res = await client.post(
                "/api/v1/predictions?diseaseType=DIABETES",
                headers=headers,
                json={"input_snapshot": {"fasting_blood_sugar": 130}},
            )
            assert res.status_code == status.HTTP_201_CREATED
            body = res.json()
            assert body["disease_type"] == "DIABETES"
            assert body["risk_level"] in {"RISK", "HIGH_RISK"}

    async def test_list_predictions_latest_filter(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="list_pred@example.com", phone_number="01022220003")
            headers = {"Authorization": f"Bearer {token}"}
            await self._seed_profile_and_bp(client, headers, 145, 95)

            await client.post("/api/v1/predictions?diseaseType=HYPERTENSION", headers=headers, json={})
            await client.post("/api/v1/predictions?diseaseType=HYPERTENSION", headers=headers, json={})
            await client.post("/api/v1/predictions?diseaseType=DIABETES", headers=headers, json={})

            res = await client.get("/api/v1/predictions?latest=true", headers=headers)
            assert res.status_code == status.HTTP_200_OK
            disease_types = {item["disease_type"] for item in res.json()["items"]}
            assert disease_types == {"HYPERTENSION", "DIABETES"}

            res_filtered = await client.get(
                "/api/v1/predictions?diseaseType=HYPERTENSION",
                headers=headers,
            )
            assert res_filtered.status_code == status.HTTP_200_OK
            assert all(item["disease_type"] == "HYPERTENSION" for item in res_filtered.json()["items"])
            assert len(res_filtered.json()["items"]) == 2

    async def test_risk_recommendations_endpoint(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="reco@example.com", phone_number="01022220004")
            headers = {"Authorization": f"Bearer {token}"}
            await self._seed_profile_and_bp(client, headers, 150, 95)
            created = await client.post("/api/v1/predictions?diseaseType=HYPERTENSION", headers=headers, json={})
            prediction_id = created.json()["id"]

            res = await client.get(
                f"/api/v1/predictions/{prediction_id}/risk-recommendations",
                headers=headers,
            )
            assert res.status_code == status.HTTP_200_OK
            body = res.json()
            assert body["prediction_id"] == prediction_id
            assert body["disclaimer"]
            assert len(body["recommendations"]) >= 1

    async def test_explanation_endpoint(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="explain@example.com", phone_number="01022220005")
            headers = {"Authorization": f"Bearer {token}"}
            await self._seed_profile_and_bp(client, headers, 150, 95)
            created = await client.post("/api/v1/predictions?diseaseType=HYPERTENSION", headers=headers, json={})
            prediction_id = created.json()["id"]

            res = await client.get(
                f"/api/v1/predictions/{prediction_id}/explanations?visualization=feature",
                headers=headers,
            )
            assert res.status_code == status.HTTP_200_OK
            body = res.json()
            assert body["visualization"] == "feature"
            assert body["charts"][0]["type"] == "feature_contribution"

    async def test_other_user_cannot_view_prediction(self):
        async with make_client() as client:
            owner_token = await signup_and_login(client, email="pred_owner@example.com", phone_number="01022220006")
            owner_headers = {"Authorization": f"Bearer {owner_token}"}
            await self._seed_profile_and_bp(client, owner_headers, 145, 92)
            created = await client.post("/api/v1/predictions?diseaseType=HYPERTENSION", headers=owner_headers, json={})
            prediction_id = created.json()["id"]

            intruder_token = await signup_and_login(
                client, email="pred_intruder@example.com", phone_number="01022220007", name="침입자"
            )
            res = await client.get(
                f"/api/v1/predictions/{prediction_id}/risk-recommendations",
                headers={"Authorization": f"Bearer {intruder_token}"},
            )
            assert res.status_code == status.HTTP_404_NOT_FOUND
