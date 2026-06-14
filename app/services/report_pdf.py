"""월간 리포트 서버사이드 PDF 렌더.

흐름: MonthlyReportService.get_or_build 가 만든 구조화 dict
  → build_report_html() (순수 함수, 단위 테스트 대상)
  → Playwright(chromium) set_content → page.pdf (bytes)
  → FileUploadService 디스크 저장 + FileUpload(REPORT_PDF) row
  → access_url(/media/...) 반환.

외부 CDN/네트워크 의존 없음: 차트/게이지는 모두 인라인 SVG 로 서버 생성하며
chromium 은 set_content 로 주입된 HTML 만 오프라인 렌더한다.
"""

from __future__ import annotations

import html
import io
import math
from datetime import datetime
from typing import Any

from app.models.files import FileType
from app.models.users import User
from app.services.files import FileUploadService

# trend metric(get_or_build _build_trends 의 metric) → (한글 라벨, 단위). 없으면 원본 key 노출.
_METRIC_LABELS: dict[str, tuple[str, str]] = {
    "blood_pressure": ("혈압", "mmHg"),
    "blood_glucose": ("혈당", "mg/dL"),
    "weight": ("체중", "kg"),
}

# DiseaseType.value → 한글 라벨.
_DISEASE_LABELS: dict[str, str] = {
    "HYPERTENSION": "고혈압",
    "DIABETES": "당뇨병",
    "CARDIOVASCULAR": "이상지질혈증",
}

# 챌린지 status → 한글 라벨.
_CHALLENGE_STATUS_LABELS: dict[str, str] = {
    "success": "성공",
    "in_progress": "진행 중",
    "failed": "미달성",
}


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _fmt_num(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _risk_gauge_svg(score: float) -> str:
    """0~100 risk_score 반원 게이지(인라인 SVG). 외부 폰트/이미지 없음."""
    score = max(0.0, min(100.0, float(score)))
    # 반원: 180도(왼쪽 끝) → 0도(오른쪽 끝). 바늘 각도 계산.
    angle_deg = 180.0 - (score / 100.0) * 180.0
    angle_rad = math.radians(angle_deg)
    cx, cy, r = 100.0, 100.0, 80.0
    nx = cx + r * math.cos(angle_rad)
    ny = cy - r * math.sin(angle_rad)
    # 위험도 색: 낮음(녹색)→높음(적색).
    if score < 30:
        color = "#22c55e"
    elif score < 60:
        color = "#eab308"
    elif score < 80:
        color = "#f97316"
    else:
        color = "#ef4444"
    return (
        f'<svg width="200" height="120" viewBox="0 0 200 120" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" '
        f'stroke="#e5e7eb" stroke-width="14" stroke-linecap="round"/>'
        f'<line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" '
        f'stroke="{color}" stroke-width="4" stroke-linecap="round"/>'
        f'<circle cx="{cx}" cy="{cy}" r="6" fill="{color}"/>'
        f'<text x="{cx}" y="80" text-anchor="middle" '
        f'font-size="22" font-weight="700" fill="{color}">{score:g}</text>'
        f"</svg>"
    )


def _line_chart_svg(points: list[float], *, label: str) -> str:
    """series(숫자 리스트) → 인라인 SVG 폴리라인. 점 0/1개도 안전."""
    if not points:
        return f'<div class="empty">{_esc(label)} 데이터가 없습니다.</div>'
    w, h, pad = 320.0, 120.0, 16.0
    lo = min(points)
    hi = max(points)
    span = (hi - lo) or 1.0
    n = len(points)
    step = (w - 2 * pad) / (n - 1) if n > 1 else 0.0

    def _x(i: int) -> float:
        return pad + step * i

    def _y(v: float) -> float:
        return h - pad - ((v - lo) / span) * (h - 2 * pad)

    if n == 1:
        coords = f"{_x(0):.1f},{_y(points[0]):.1f} {w - pad:.1f},{_y(points[0]):.1f}"
    else:
        coords = " ".join(f"{_x(i):.1f},{_y(v):.1f}" for i, v in enumerate(points))
    dots = "".join(f'<circle cx="{_x(i):.1f}" cy="{_y(v):.1f}" r="2.5" fill="#2563eb"/>' for i, v in enumerate(points))
    return (
        f'<svg width="{w:g}" height="{h:g}" viewBox="0 0 {w:g} {h:g}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f'<polyline points="{coords}" fill="none" stroke="#2563eb" stroke-width="2"/>'
        f"{dots}</svg>"
    )


def _progress_bar(ratio: float) -> str:
    pct = max(0.0, min(100.0, ratio * 100.0))
    return (
        f'<div class="bar-track"><div class="bar-fill" style="width:{pct:.0f}%"></div></div>'
        f'<span class="bar-pct">{pct:.0f}%</span>'
    )


def _header_section(report: dict[str, Any], header: dict[str, Any]) -> str:
    year_month = _esc(report.get("year_month", ""))
    generated_at = report.get("generated_at")
    if isinstance(generated_at, datetime):
        generated_str = _esc(generated_at.strftime("%Y-%m-%d %H:%M"))
    else:
        generated_str = _esc(generated_at)
    recorded_days = header.get("recorded_days", 0) if isinstance(header, dict) else 0
    avg_steps = header.get("avg_steps") if isinstance(header, dict) else None
    avg_sleep = header.get("avg_sleep_hours") if isinstance(header, dict) else None
    return (
        f'<header class="report-header">'
        f"<h1>케어로그 월간 건강 리포트</h1>"
        f'<div class="meta">{year_month} · 생성 {generated_str}</div>'
        f'<div class="stat-row">'
        f'<div class="stat"><div class="stat-num">{_esc(recorded_days)}</div><div class="stat-cap">기록한 날</div></div>'
        f'<div class="stat"><div class="stat-num">{_fmt_num(avg_steps)}</div><div class="stat-cap">평균 걸음 수</div></div>'
        f'<div class="stat"><div class="stat-num">{_fmt_num(avg_sleep)}</div><div class="stat-cap">평균 수면(시간)</div></div>'
        f"</div></header>"
    )


def _risk_section(disease_risks: list[dict[str, Any]]) -> str:
    if not disease_risks:
        return '<section><h2>위험도 평가</h2><div class="empty">이번 달 위험도 평가 기록이 없습니다.</div></section>'
    gauges = []
    for info in disease_risks:
        if not isinstance(info, dict):
            continue
        label = _DISEASE_LABELS.get(info.get("disease_type", ""), info.get("disease_type", ""))
        if info.get("has_prediction"):
            level = info.get("risk_level_label") or info.get("risk_level") or ""
            body = _risk_gauge_svg(float(info.get("risk_score") or 0.0))
            level_html = f'<div class="gauge-level">{_esc(level)}</div>'
        else:
            body = '<div class="empty">예측 데이터가 없습니다.</div>'
            level_html = '<div class="gauge-level">예측 없음</div>'
        gauges.append(
            f'<div class="gauge-card"><div class="gauge-title">{_esc(label)}</div>'
            f"{body}{level_html}</div>"
        )
    return f'<section><h2>위험도 평가</h2><div class="gauge-row">{"".join(gauges)}</div></section>'


def _factors_section(disease_risks: list[dict[str, Any]]) -> str:
    blocks = []
    for info in disease_risks:
        if not isinstance(info, dict) or not info.get("has_prediction"):
            continue
        factors = info.get("top_factors") or []
        items = "".join(
            f'<li>{_esc(f.get("name_kor") or f.get("factor") or "")} '
            f'<span class="dir">{_esc(f.get("direction") or "")}</span></li>'
            for f in factors
            if isinstance(f, dict)
        )
        if not items:
            continue
        label = _DISEASE_LABELS.get(info.get("disease_type", ""), info.get("disease_type", ""))
        blocks.append(f'<div class="factor-group"><h3>{_esc(label)}</h3><ol class="factors">{items}</ol></div>')
    if not blocks:
        return ""
    return f'<section><h2>판단 근거 TOP5</h2>{"".join(blocks)}</section>'


def _trend_section(trends: list[dict[str, Any]]) -> str:
    blocks = []
    for t in trends:
        if not isinstance(t, dict):
            continue
        series = t.get("series") or []
        nums = [float(p["value"]) for p in series if isinstance(p, dict) and p.get("value") is not None]
        if not nums:
            continue
        label = _METRIC_LABELS.get(t.get("metric", ""), (t.get("metric", ""), ""))[0]
        blocks.append(
            f'<div class="trend-card"><div class="trend-title">{_esc(label)} 추이</div>'
            f"{_line_chart_svg(nums, label=label)}</div>"
        )
    if not blocks:
        return ""
    return f'<section><h2>측정 추이</h2><div class="trend-row">{"".join(blocks)}</div></section>'


def _stats_section(trends: list[dict[str, Any]]) -> str:
    rows = []
    for t in trends:
        if not isinstance(t, dict):
            continue
        series = t.get("series") or []
        if not series:
            continue
        label, default_unit = _METRIC_LABELS.get(t.get("metric", ""), (t.get("metric", ""), ""))
        unit = t.get("unit") or default_unit
        rows.append(
            f"<tr><td>{_esc(label)}</td>"
            f"<td>{len(series)}</td>"
            f"<td>{_fmt_num(t.get('latest'))}</td>"
            f"<td>{_fmt_num(t.get('avg'))} {_esc(unit)}</td></tr>"
        )
    if not rows:
        return '<section><h2>측정 요약</h2><div class="empty">이번 달 측정 기록이 없습니다.</div></section>'
    return (
        '<section><h2>측정 요약</h2><table class="stats">'
        "<thead><tr><th>항목</th><th>측정 횟수</th><th>최근값</th><th>평균</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></section>"
    )


def _challenge_section(challenges: list[dict[str, Any]]) -> str:
    if not challenges:
        return '<section><h2>챌린지 내역</h2><div class="empty">이번 달 챌린지 참여 내역이 없습니다.</div></section>'
    rows = []
    for c in challenges:
        if not isinstance(c, dict):
            continue
        ratio = float(c.get("progress_percent", 0) or 0) / 100.0
        state = _CHALLENGE_STATUS_LABELS.get(c.get("status", ""), c.get("status", ""))
        rows.append(
            f'<div class="challenge-row"><span class="ch-title">{_esc(c.get("title", ""))}</span>'
            f"{_progress_bar(ratio)}"
            f'<span class="ch-state">{_esc(state)}</span></div>'
        )
    return f'<section><h2>챌린지 내역</h2>{"".join(rows)}</section>'


def _habits_section(good_habits: list[dict[str, Any]]) -> str:
    if not good_habits:
        return ""
    items = "".join(
        f'<li><b>{_esc(h.get("label") or "")}</b> '
        f'<span class="dir">{_esc(h.get("evidence") or "")}</span></li>'
        for h in good_habits
        if isinstance(h, dict)
    )
    if not items:
        return ""
    return f'<section><h2>이달의 좋은 습관</h2><ul class="habits">{items}</ul></section>'


def build_report_html(report: dict[str, Any]) -> str:
    """구조화 리포트 dict → print 용 HTML 문자열(순수 함수).

    payload 에 없는 섹션은 빈 안내로 안전하게 처리(데이터 없는 월 대응).
    """
    header: dict[str, Any] = report.get("header_stats") or {}
    disease_risks: list[dict[str, Any]] = report.get("disease_risks") or []
    trends: list[dict[str, Any]] = report.get("trends") or []
    challenges: list[dict[str, Any]] = report.get("challenges") or []
    good_habits: list[dict[str, Any]] = report.get("good_habits") or []

    sections = (
        _header_section(report, header)
        + _risk_section(disease_risks)
        + _factors_section(disease_risks)
        + _trend_section(trends)
        + _stats_section(trends)
        + _challenge_section(challenges)
        + _habits_section(good_habits)
    )

    disclaimer_html = (
        '<footer class="disclaimer">본 리포트는 사용자가 입력한 기록을 요약한 참고 자료이며, '
        "의학적 진단이나 처방을 대체하지 않습니다. 건강 관련 결정은 반드시 의료 전문가와 상의하세요.</footer>"
    )

    style = """
    <style>
      * { box-sizing: border-box; }
      body {
        font-family: 'Nanum Gothic', 'Noto Sans CJK KR', 'Malgun Gothic', sans-serif;
        color: #111827; margin: 0; padding: 28px 32px; font-size: 13px;
      }
      h1 { font-size: 22px; margin: 0 0 4px; }
      h2 { font-size: 15px; margin: 22px 0 10px; padding-bottom: 4px; border-bottom: 2px solid #2563eb; }
      h3 { font-size: 13px; margin: 10px 0 4px; color: #374151; }
      .factor-group { margin-bottom: 8px; }
      .report-header .meta { color: #6b7280; font-size: 12px; }
      .stat-row { display: flex; gap: 14px; margin-top: 14px; }
      .stat { flex: 1; background: #f3f4f6; border-radius: 8px; padding: 12px; text-align: center; }
      .stat-num { font-size: 20px; font-weight: 700; color: #2563eb; }
      .stat-cap { font-size: 11px; color: #6b7280; margin-top: 2px; }
      .gauge-row, .trend-row { display: flex; gap: 16px; flex-wrap: wrap; }
      .gauge-card, .trend-card { text-align: center; flex: 1; min-width: 180px; }
      .gauge-title, .trend-title { font-weight: 700; margin-bottom: 4px; }
      .gauge-level { color: #6b7280; font-size: 12px; }
      table.stats { width: 100%; border-collapse: collapse; }
      table.stats th, table.stats td { border: 1px solid #e5e7eb; padding: 6px 8px; text-align: center; }
      table.stats th { background: #f9fafb; }
      ol.factors, ul.habits { margin: 0; padding-left: 20px; }
      ol.factors li, ul.habits li { margin: 4px 0; }
      .factors .dir { color: #6b7280; font-size: 11px; }
      .challenge-row { display: flex; align-items: center; gap: 10px; margin: 6px 0; }
      .ch-title { width: 130px; }
      .bar-track { flex: 1; height: 10px; background: #e5e7eb; border-radius: 5px; overflow: hidden; }
      .bar-fill { height: 100%; background: #2563eb; }
      .bar-pct { width: 40px; text-align: right; font-size: 11px; color: #6b7280; }
      .ch-state { width: 52px; text-align: right; font-size: 11px; color: #374151; }
      .empty { color: #9ca3af; font-size: 12px; padding: 8px 0; }
      .disclaimer { margin-top: 28px; padding-top: 12px; border-top: 1px solid #e5e7eb;
        color: #9ca3af; font-size: 11px; line-height: 1.5; }
    </style>
    """

    return (
        '<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"/>'
        f"{style}</head><body>"
        f"{sections}{disclaimer_html}"
        "</body></html>"
    )


async def render_pdf_bytes(html_str: str) -> bytes:
    """HTML 문자열 → A4 PDF bytes (Playwright chromium, set_content 오프라인 렌더).

    URL 네비게이션/인증 불필요 — set_content 로 직접 주입한다.
    온디맨드·저빈도라 per-request launch(브라우저 1회 기동 후 즉시 종료)로 단순화.
    동시 호출 시에도 각자 독립된 브라우저 프로세스를 쓰므로 상태 공유 없음.
    """
    from playwright.async_api import async_playwright  # type: ignore[import-not-found]

    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        try:
            page = await browser.new_page()
            await page.set_content(html_str, wait_until="networkidle")
            pdf_bytes = await page.pdf(format="A4", print_background=True)
        finally:
            await browser.close()
    return pdf_bytes


class ReportPdfService:
    """리포트 dict → PDF 생성 → 파일 저장 → access_url."""

    def __init__(self) -> None:
        self.files = FileUploadService()

    async def build_and_store(self, user: User, report: dict[str, Any]) -> str:
        html_str = build_report_html(report)
        pdf_bytes = await render_pdf_bytes(html_str)
        year_month = str(report.get("year_month", "report"))
        original_name = f"care_report_{year_month}.pdf"
        upload = await self.files.upload(
            user,
            upload_file_stream=io.BytesIO(pdf_bytes),
            original_name=original_name,
            mime_type="application/pdf",
            file_type=FileType.REPORT_PDF,
        )
        return upload.access_url


__all__ = ["ReportPdfService", "build_report_html", "render_pdf_bytes"]
