from starlette import status
from tortoise.contrib.test import TestCase

from app.tests.health_apis.helpers import make_client, signup_and_login


class TestHealthStatisticsApi(TestCase):
    async def test_blood_pressure_insufficient_data(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="bp_stat@example.com", phone_number="01033330001")
            headers = {"Authorization": f"Bearer {token}"}
            await client.post(
                "/api/v1/health-records",
                headers=headers,
                json={
                    "record_type": "BLOOD_PRESSURE",
                    "sub_type": "HOSPITAL",
                    "primary_value": 120,
                    "secondary_value": 80,
                    "unit": "mmHg",
                    "measured_at": "2026-05-01T09:00:00+09:00",
                },
            )

            res = await client.get(
                "/api/v1/health-records/statistics?metric=blood_pressure",
                headers=headers,
            )
            assert res.status_code == status.HTTP_200_OK
            body = res.json()
            assert body["data_count"] == 1
            assert body["insufficient_data"] is True

    async def test_hba1c_level_categorization(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="hba1c@example.com", phone_number="01033330002")
            headers = {"Authorization": f"Bearer {token}"}
            for v, day in [(5.4, "01"), (6.0, "10"), (6.7, "20")]:
                await client.post(
                    "/api/v1/health-records",
                    headers=headers,
                    json={
                        "record_type": "HBA1C",
                        "primary_value": v,
                        "unit": "%",
                        "measured_at": f"2026-05-{day}T08:00:00+09:00",
                    },
                )
            res = await client.get(
                "/api/v1/health-records/statistics?metric=hba1c&limit=4",
                headers=headers,
            )
            assert res.status_code == status.HTTP_200_OK
            body = res.json()
            levels = {point["level"] for point in body["series"]}
            assert levels == {"normal", "pre_diabetic", "diabetic"}
            assert body["data_count"] == 3

    async def test_unknown_metric_returns_400(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="metric_fail@example.com", phone_number="01033330003")
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.get(
                "/api/v1/health-records/statistics?metric=cholesterol",
                headers=headers,
            )
            assert res.status_code == status.HTTP_400_BAD_REQUEST
