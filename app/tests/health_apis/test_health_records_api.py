from starlette import status
from tortoise.contrib.test import TestCase

from app.tests.health_apis.helpers import make_client, signup_and_login


class TestHealthRecordsApi(TestCase):
    async def test_upsert_and_get_profile(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="profile@example.com", phone_number="01011110001")
            headers = {"Authorization": f"Bearer {token}"}

            res = await client.post(
                "/api/v1/health-records?recordType=profile",
                headers=headers,
                json={
                    "height_cm": 175,
                    "weight_kg": 70,
                    "waist_cm": 82,
                    "current_smoker": 0,
                    "alcohol_freq_y": 4,
                    "family_dm": 1,
                    "family_hp": 0,
                },
            )
            assert res.status_code == status.HTTP_201_CREATED
            assert res.json()["height_cm"] == "175.0"
            assert res.json()["family_dm"] == 1

            res2 = await client.get("/api/v1/health-records?recordType=profile", headers=headers)
            assert res2.status_code == status.HTTP_200_OK
            assert res2.json()["weight_kg"] == "70.0"

    async def test_create_blood_pressure_record_home_correction(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="bp@example.com", phone_number="01011110002")
            headers = {"Authorization": f"Bearer {token}"}

            res = await client.post(
                "/api/v1/health-records",
                headers=headers,
                json={
                    "record_type": "BLOOD_PRESSURE",
                    "sub_type": "HOME",
                    "primary_value": 125,
                    "secondary_value": 82,
                    "unit": "mmHg",
                    "measured_at": "2026-05-10T08:00:00+09:00",
                    "source": "MANUAL",
                },
            )
            assert res.status_code == status.HTTP_201_CREATED
            body = res.json()
            # 가정 측정값 자동 보정 +5/+5
            assert float(body["primary_value"]) == 130.0
            assert float(body["secondary_value"]) == 87.0
            assert body["sub_type"] == "HOME"

    async def test_blood_pressure_requires_diastolic(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="bp_fail@example.com", phone_number="01011110003")
            headers = {"Authorization": f"Bearer {token}"}

            res = await client.post(
                "/api/v1/health-records",
                headers=headers,
                json={
                    "record_type": "BLOOD_PRESSURE",
                    "sub_type": "HOSPITAL",
                    "primary_value": 130,
                    "unit": "mmHg",
                    "measured_at": "2026-05-10T08:00:00+09:00",
                },
            )
            assert res.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_list_filter_by_record_type_and_period(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="list@example.com", phone_number="01011110004")
            headers = {"Authorization": f"Bearer {token}"}

            for value, day in [(80.0, "01"), (78.5, "02"), (76.0, "03")]:
                await client.post(
                    "/api/v1/health-records",
                    headers=headers,
                    json={
                        "record_type": "WEIGHT",
                        "primary_value": value,
                        "unit": "kg",
                        "measured_at": f"2026-05-{day}T09:00:00+09:00",
                    },
                )

            res = await client.get(
                "/api/v1/health-records?recordType=WEIGHT&from=2026-05-01&to=2026-05-02",
                headers=headers,
            )
            assert res.status_code == status.HTTP_200_OK
            body = res.json()
            assert body["total_elements"] == 2
            assert len(body["items"]) == 2

    async def test_update_and_delete_owned_record(self):
        async with make_client() as client:
            token = await signup_and_login(client, email="modify@example.com", phone_number="01011110005")
            headers = {"Authorization": f"Bearer {token}"}

            create = await client.post(
                "/api/v1/health-records",
                headers=headers,
                json={
                    "record_type": "WAIST",
                    "primary_value": 85,
                    "unit": "cm",
                    "measured_at": "2026-05-10T08:00:00+09:00",
                },
            )
            record_id = create.json()["id"]

            patch = await client.patch(
                f"/api/v1/health-records/{record_id}",
                headers=headers,
                json={"primary_value": 84, "note": "회복 중"},
            )
            assert patch.status_code == status.HTTP_200_OK
            assert float(patch.json()["primary_value"]) == 84.0

            delete = await client.delete(f"/api/v1/health-records/{record_id}", headers=headers)
            assert delete.status_code == status.HTTP_204_NO_CONTENT

            # 소프트 삭제 후 조회 불가
            res = await client.get(f"/api/v1/health-records/{record_id}", headers=headers)
            assert res.status_code == status.HTTP_404_NOT_FOUND

    async def test_other_user_cannot_access_record(self):
        async with make_client() as client:
            owner_token = await signup_and_login(client, email="owner@example.com", phone_number="01011110006")
            owner_headers = {"Authorization": f"Bearer {owner_token}"}
            create = await client.post(
                "/api/v1/health-records",
                headers=owner_headers,
                json={
                    "record_type": "WEIGHT",
                    "primary_value": 70,
                    "unit": "kg",
                    "measured_at": "2026-05-10T08:00:00+09:00",
                },
            )
            record_id = create.json()["id"]

            intruder_token = await signup_and_login(
                client, email="intruder@example.com", phone_number="01011110007", name="침입자"
            )
            intruder_headers = {"Authorization": f"Bearer {intruder_token}"}
            res = await client.get(f"/api/v1/health-records/{record_id}", headers=intruder_headers)
            assert res.status_code == status.HTTP_404_NOT_FOUND

    async def test_records_require_auth(self):
        async with make_client() as client:
            res = await client.get("/api/v1/health-records")
            assert res.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}
