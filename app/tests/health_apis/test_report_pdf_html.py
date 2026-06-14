"""build_report_html 순수 함수 단위 테스트 (chromium/디스크 불필요).

get_or_build 가 내보내는 신스키마(header_stats / disease_risks / trends /
challenges / good_habits)를 기준으로, 데이터 유/무 양쪽에서 섹션 포함·null-safe 를 검증한다.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.services.report_pdf import ReportPdfService, build_report_html


def test_html_with_full_data_contains_all_sections():
    report = {
        "year_month": "2026-05",
        "generated_at": datetime(2026, 5, 14, 9, 30),
        "header_stats": {"recorded_days": 12, "avg_sleep_hours": 7.2, "avg_steps": 10000.0},
        "disease_risks": [
            {
                "disease_type": "HYPERTENSION",
                "risk_score": 72.0,
                "risk_level": "RISK",
                "risk_level_label": "위험",
                "calculated_at": "2026-05-10T09:00:00",
                "has_prediction": True,
                "top_factors": [
                    {"factor": "sbp", "weight": 0.9, "name_kor": "수축기 혈압", "direction": "위험 증가↑"},
                    {"factor": "weight", "weight": 0.5, "name_kor": "체중", "direction": "위험 증가↑"},
                ],
            },
            {
                "disease_type": "CARDIOVASCULAR",
                "risk_score": None,
                "risk_level": None,
                "risk_level_label": None,
                "calculated_at": None,
                "has_prediction": False,
                "top_factors": [],
            },
        ],
        "trends": [
            {
                "metric": "weight",
                "unit": "kg",
                "series": [
                    {"date": "2026-05-05", "value": 70.0, "secondary_value": None},
                    {"date": "2026-05-12", "value": 71.0, "secondary_value": None},
                    {"date": "2026-05-20", "value": 72.0, "secondary_value": None},
                ],
                "avg": 71.0,
                "latest": 72.0,
                "secondary_avg": None,
                "secondary_latest": None,
            },
        ],
        "challenges": [
            {
                "challenge_id": 1,
                "title": "매일 걷기",
                "category": "EXERCISE",
                "status": "in_progress",
                "progress_percent": 80,
                "success_days": 8,
                "goal_days": 10,
            },
        ],
        "good_habits": [
            {"key": "walking", "label": "꾸준한 걷기", "evidence": "이번 달 평균 10,000걸음을 기록했어요."},
        ],
    }
    html = build_report_html(report)

    assert "케어로그 월간 건강 리포트" in html
    assert "2026-05" in html
    assert "위험도 평가" in html
    assert "고혈압" in html  # 한글 라벨 매핑
    assert "이상지질혈증" in html  # CARDIOVASCULAR 라벨
    assert "예측 없음" in html  # has_prediction False 게이지
    assert "판단 근거 TOP5" in html
    assert "수축기 혈압" in html
    assert "측정 추이" in html
    assert "측정 요약" in html
    assert "체중" in html
    assert "챌린지 내역" in html
    assert "매일 걷기" in html
    assert "진행 중" in html  # status 한글 라벨
    assert "이달의 좋은 습관" in html
    assert "꾸준한 걷기" in html
    assert "<svg" in html  # 인라인 게이지/라인차트 SVG
    assert "<!DOCTYPE html>" in html


def test_html_with_empty_data_is_null_safe():
    report = {
        "year_month": "2026-06",
        "generated_at": datetime(2026, 6, 1, 0, 0),
        "header_stats": {"recorded_days": 0, "avg_sleep_hours": None, "avg_steps": None},
        "disease_risks": [],
        "trends": [],
        "challenges": [],
        "good_habits": [],
    }
    html = build_report_html(report)

    # 빈 섹션은 안내 문구로 안전 처리, 예외 없이 문자열 반환.
    assert "이번 달 위험도 평가 기록이 없습니다." in html
    assert "이번 달 측정 기록이 없습니다." in html
    assert "이번 달 챌린지 참여 내역이 없습니다." in html
    # 데이터 없는 선택 섹션은 아예 생략.
    assert "판단 근거 TOP5" not in html
    assert "측정 추이" not in html
    assert "이달의 좋은 습관" not in html


def test_html_handles_missing_keys():
    # get_or_build payload 형태가 아니어도(키 누락) 예외 없이 렌더.
    html = build_report_html({"year_month": "2026-07", "generated_at": None})
    assert "케어로그 월간 건강 리포트" in html
    assert "2026-07" in html


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("2026-05", "care_report_2026-05.pdf"),
        # 개행/따옴표 등 헤더 인젝션 시도 → 안전 문자만 남김.
        ('2026-05"\r\nSet-Cookie: x', "care_report_2026-05Set-Cookiex.pdf"),
        ("2026-05\n", "care_report_2026-05.pdf"),
        ("/../../etc", "care_report_etc.pdf"),
    ],
)
async def test_build_bytes_filename_is_header_safe(raw, expected):
    # build_bytes 의 다운로드 파일명은 Content-Disposition 에 들어가므로
    # 사용자 유래 year_month 의 위험 문자를 제거해야 한다. (chromium 은 목으로 대체)
    with patch("app.services.report_pdf.render_pdf_bytes", AsyncMock(return_value=b"%PDF-1.4")):
        pdf_bytes, filename = await ReportPdfService().build_bytes({"year_month": raw})
    assert pdf_bytes == b"%PDF-1.4"
    assert filename == expected
    assert "\n" not in filename and "\r" not in filename and '"' not in filename
