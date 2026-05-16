from starlette import status
from tortoise.contrib.test import TestCase

from app.tests.health_apis.helpers import make_client, signup_and_login


class TestHealthReportApi(TestCase):
    async def test_monthly_report_returns_summary(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="report@example.com", phone_number="01044440001")
            headers = {"Authorization": f"Bearer {token}"}
            await client.post(
                "/api/v1/health-records?recordType=profile",
                headers=headers,
                json={"height_cm": 170, "weight_kg": 72, "waist_cm": 80},
            )
            for v, day in [(70.0, "05"), (71.0, "12"), (72.0, "20")]:
                await client.post(
                    "/api/v1/health-records",
                    headers=headers,
                    json={
                        "record_type": "WEIGHT",
                        "primary_value": v,
                        "unit": "kg",
                        "measured_at": f"2026-05-{day}T08:00:00+09:00",
                    },
                )

            res = await client.get(
                "/api/v1/health-reports?period=monthly&month=2026-05",
                headers=headers,
            )
            assert res.status_code == status.HTTP_200_OK
            body = res.json()
            assert body["year_month"] == "2026-05"
            assert "WEIGHT" in body["health_data_summary"]
            assert body["health_data_summary"]["WEIGHT"]["count"] == 3

    async def test_invalid_month_returns_400(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="report_fail@example.com", phone_number="01044440002")
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.get(
                "/api/v1/health-reports?period=monthly&month=2026-13",
                headers=headers,
            )
            assert res.status_code == status.HTTP_400_BAD_REQUEST

    async def test_pdf_not_implemented(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="report_pdf@example.com", phone_number="01044440003")
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.get(
                "/api/v1/health-reports?period=monthly&month=2026-05&format=pdf",
                headers=headers,
            )
            assert res.status_code == status.HTTP_501_NOT_IMPLEMENTED
