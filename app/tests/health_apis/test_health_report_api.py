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

    async def test_pdf_returns_pdf_url(self):
        # 실제 chromium/디스크 저장은 무거우므로 build_and_store 를 목으로 대체.
        # 라우터가 PDF 경로에서 200 + pdf_url 을 채워 응답하는지만 검증.
        from unittest.mock import AsyncMock, patch

        async with make_client() as client:
            token = await signup_and_login(client, email="report_pdf@example.com", phone_number="01044440003")
            headers = {"Authorization": f"Bearer {token}"}
            fake_url = "/media/uploads/report_pdf/20260514/1/abc.pdf"
            with patch(
                "app.apis.v1.health_routers.ReportPdfService.build_and_store",
                AsyncMock(return_value=fake_url),
            ):
                res = await client.get(
                    "/api/v1/health-reports?period=monthly&month=2026-05&format=pdf",
                    headers=headers,
                )
            assert res.status_code == status.HTTP_200_OK
            assert res.json()["pdf_url"] == fake_url

    async def test_empty_month_is_null_safe(self):
        """데이터 없는 월: 빈/널 안전. 질환 3종은 has_prediction=False 로 모두 노출."""
        async with make_client() as client:
            token = await signup_and_login(client, email="report_empty@example.com", phone_number="01044440004")
            headers = {"Authorization": f"Bearer {token}"}
            res = await client.get(
                "/api/v1/health-reports?period=monthly&month=2026-01",
                headers=headers,
            )
            assert res.status_code == status.HTTP_200_OK
            body = res.json()
            assert body["header_stats"]["recorded_days"] == 0
            assert body["header_stats"]["avg_steps"] is None
            assert body["trends"] == [] or all(t["series"] == [] for t in body["trends"])
            assert body["challenges"] == []
            assert body["good_habits"] == []
            # 질환 3종 모두 노출되며 예측 없음
            assert len(body["disease_risks"]) == 3
            assert all(d["has_prediction"] is False for d in body["disease_risks"])

    async def test_header_and_trends_aggregation(self):
        """헤더(기록일수/걸음/수면) + 추이(혈압/혈당/체중) 집계 검증."""
        async with make_client() as client:
            token = await signup_and_login(client, email="report_trend@example.com", phone_number="01044440005")
            headers = {"Authorization": f"Bearer {token}"}
            # 체중 3일
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
            # 혈압 2일 (병원 측정: 보정 없음)
            for sys_v, dia_v, day in [(120.0, 80.0, "05"), (130.0, 85.0, "12")]:
                await client.post(
                    "/api/v1/health-records",
                    headers=headers,
                    json={
                        "record_type": "BLOOD_PRESSURE",
                        "sub_type": "HOSPITAL",
                        "primary_value": sys_v,
                        "secondary_value": dia_v,
                        "unit": "mmHg",
                        "measured_at": f"2026-05-{day}T09:00:00+09:00",
                    },
                )
            # 걸음 (ACTIVITY) 2일
            for steps, day in [(9000.0, "05"), (11000.0, "12")]:
                await client.post(
                    "/api/v1/health-records",
                    headers=headers,
                    json={
                        "record_type": "ACTIVITY",
                        "primary_value": steps,
                        "unit": "steps",
                        "measured_at": f"2026-05-{day}T20:00:00+09:00",
                    },
                )

            res = await client.get(
                "/api/v1/health-reports?period=monthly&month=2026-05",
                headers=headers,
            )
            assert res.status_code == status.HTTP_200_OK
            body = res.json()
            # 기록일수: 05, 12, 20 → 3일
            assert body["header_stats"]["recorded_days"] == 3
            assert body["header_stats"]["avg_steps"] == 10000.0

            trends = {t["metric"]: t for t in body["trends"]}
            assert trends["weight"]["latest"] == 72.0
            assert trends["weight"]["avg"] == 71.0
            assert len(trends["weight"]["series"]) == 3
            assert trends["blood_pressure"]["secondary_avg"] == 82.5
            assert trends["blood_pressure"]["latest"] == 130.0

            # 걷기 평균 8000 이상 → 좋은 습관 'walking' 도출
            habit_keys = {h["key"] for h in body["good_habits"]}
            assert "walking" in habit_keys

    async def test_risk_top_factors(self):
        """위험도 판단근거 TOP5: weight 절댓값 내림차순 정렬 + name_kor/direction 노출."""
        from app.models.health import DiseaseRisk, DiseaseType, RiskLevel
        from app.models.users import User

        async with make_client() as client:
            token = await signup_and_login(client, email="report_risk@example.com", phone_number="01044440006")
            headers = {"Authorization": f"Bearer {token}"}
            user = await User.get(email="report_risk@example.com")
            factors = [
                {"factor": f"f{i}", "weight": w, "name_kor": f"요인{i}", "direction": "위험 증가↑"}
                for i, w in enumerate([0.1, 0.9, 0.5, 0.7, 0.3, 0.2])
            ]
            await DiseaseRisk.create(
                user_id=user.id,
                disease_type=DiseaseType.HYPERTENSION,
                risk_score=72,
                risk_level=RiskLevel.RISK,
                contributing_factors=factors,
                input_snapshot={},
                model_version="test",
                calculated_at=__import__("datetime").datetime(2026, 5, 10, 9, 0),
            )
            res = await client.get(
                "/api/v1/health-reports?period=monthly&month=2026-05",
                headers=headers,
            )
            assert res.status_code == status.HTTP_200_OK
            body = res.json()
            hyp = next(d for d in body["disease_risks"] if d["disease_type"] == "HYPERTENSION")
            assert hyp["has_prediction"] is True
            assert hyp["risk_score"] == 72.0
            weights = [f["weight"] for f in hyp["top_factors"]]
            assert weights == [0.9, 0.7, 0.5, 0.3, 0.2]  # TOP5, 절댓값 내림차순
            assert hyp["top_factors"][0]["name_kor"] == "요인1"


def test_build_trends_secondary_latest_with_trailing_none() -> None:
    """_build_trends: 마지막 혈압 레코드에 이완기(secondary)가 없어도 secondary_latest 가 마지막 '유효'값.

    secondary_value 는 nullable — matched[-1].secondary_value 직접 캐스트 시 None→TypeError 였던 회귀 방지.
    DB 불필요(순수 classmethod, 미저장 HealthRecord 인스턴스로 검증).
    """
    from datetime import datetime
    from decimal import Decimal

    from app.core import config
    from app.models.health import HealthRecord, RecordType
    from app.services.health import MonthlyReportService

    def _bp(sys_v: float, dia_v: float | None, day: int) -> HealthRecord:
        return HealthRecord(
            record_type=RecordType.BLOOD_PRESSURE,
            primary_value=Decimal(str(sys_v)),
            secondary_value=(Decimal(str(dia_v)) if dia_v is not None else None),
            unit="mmHg",
            measured_at=datetime(2026, 5, day, 9, 0, tzinfo=config.TIMEZONE),
            sub_type=None,
        )

    # 마지막(가장 최근) 레코드의 이완기 누락
    records = [_bp(120, 80, 5), _bp(130, None, 12)]
    bp_trend = next(t for t in MonthlyReportService._build_trends(records) if t["metric"] == "blood_pressure")
    assert bp_trend["latest"] == 130.0
    assert bp_trend["secondary_latest"] == 80.0  # 마지막 유효 이완기 (None 캐스트 회피)
    assert bp_trend["secondary_avg"] == 80.0
