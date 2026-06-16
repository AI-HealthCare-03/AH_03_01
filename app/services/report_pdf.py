"""월간 리포트 서버사이드 PDF 렌더.

흐름: MonthlyReportService.get_or_build 가 만든 구조화 dict
  → build_report_html() (순수 함수, 단위 테스트 대상)
  → Playwright(chromium) set_content → page.pdf (bytes)
  → 인증된 라우트가 응답 본문으로 즉시 다운로드(attachment) 시켜 줌.

PHI(혈압·혈당·위험도) 가 담긴 PDF 는 디스크에 영속하지 않는다 — 무인증·무만료
정적(/media) 서빙으로 노출되는 것을 막기 위해, 매 요청마다 메모리상에서만 렌더하고
인증된 사용자에게 바로 흘려보낸다.

외부 CDN/네트워크 의존 없음: 차트/게이지는 모두 인라인 SVG 로 서버 생성하며
chromium 은 set_content 로 주입된 HTML 만 오프라인 렌더한다.
"""

from __future__ import annotations

import html
import math
import re
from datetime import datetime
from typing import Any

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


# metric → (y domain, y축 눈금, 기준 구간 밴드[y1,y2,배경색,글자색,라벨], 라인[이름,값 키,색]).
# domain/ticks 가 None 이면 데이터 기반 자동 스케일(체중 등 고정 기준치가 없는 지표).
_TREND_CHART_CONFIGS: dict[str, dict[str, Any]] = {
    "blood_pressure": {
        "domain": (40.0, 200.0),
        "ticks": [40, 80, 120, 160, 200],
        "bands": [
            (60, 120, "#e8f5e9", "#2e7d32", "정상"),
            (120, 140, "#fffbe6", "#856404", "주의"),
            (140, 200, "#ffeaea", "#e53935", "위험"),
        ],
        "lines": [("수축기", "value", "#dc2626"), ("이완기", "secondary_value", "#2563eb")],
    },
    "blood_glucose": {
        "domain": (60.0, 250.0),
        "ticks": [60, 110, 160, 210, 250],
        "bands": [
            (60, 100, "#e8f5e9", "#2e7d32", "정상"),
            (100, 140, "#fffbe6", "#856404", "주의"),
            (140, 250, "#ffeaea", "#e53935", "위험"),
        ],
        "lines": [("공복혈당", "value", "#2563eb")],
    },
    "weight": {"domain": None, "ticks": None, "bands": [], "lines": [("체중", "value", "#2563eb")]},
}


def _nice_ceil(v: float) -> float:
    """v 이상인 '보기 좋은' 눈금 최대값(체중 등 고정 기준치가 없는 지표의 자동 도메인용)."""
    if v <= 0:
        return 10.0
    magnitude = 10 ** math.floor(math.log10(v))
    for m in (1, 2, 2.5, 4, 5, 8, 10):
        if magnitude * m >= v:
            return magnitude * m
    return magnitude * 10


def _to_float(value: Any) -> float | None:
    """DB에 비숫자 문자열("N/A" 등)이 들어있어도 PDF 생성이 죽지 않도록 안전 변환."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_md(iso_date: str) -> str:
    """ISO 'YYYY-MM-DD' → 'M/d' (0 제거)."""
    try:
        _, mm, dd = iso_date.split("-")
        return f"{int(mm)}/{int(dd)}"
    except ValueError:
        return iso_date


def _trend_chart_svg(trend: dict[str, Any]) -> str:
    """트렌드 dict(metric/unit/series/avg/secondary_avg) → 축·기준구간·범례·평균배지 포함 SVG."""
    metric = trend.get("metric", "")
    unit = trend.get("unit", "")
    series: list[dict[str, Any]] = trend.get("series") or []
    label = _METRIC_LABELS.get(metric, (metric, unit))[0]
    points = [p for p in series if isinstance(p, dict) and _to_float(p.get("value")) is not None]
    if not points:
        return f'<div class="empty">{_esc(label)} 데이터가 없습니다.</div>'

    cfg = _TREND_CHART_CONFIGS.get(metric, {"domain": None, "ticks": None, "bands": [], "lines": [(label, "value", "#2563eb")]})
    values = [v for p in points if (v := _to_float(p["value"])) is not None]
    if cfg["domain"] is not None:
        lo, hi = cfg["domain"]
        ticks: list[float] = cfg["ticks"]
    else:
        hi = _nice_ceil(max(values) * 1.2)
        lo = 0.0
        ticks = [hi * i / 4 for i in range(5)]

    w, h = 680.0, 260.0
    plot_left, plot_right, plot_top, plot_bottom = 54.0, 668.0, 34.0, 214.0
    span = (hi - lo) or 1.0
    n = len(points)
    step = (plot_right - plot_left) / (n - 1) if n > 1 else 0.0

    def _x(i: int) -> float:
        return plot_left + step * i

    def _y(v: float) -> float:
        return plot_bottom - ((v - lo) / span) * (plot_bottom - plot_top)

    bands_svg = "".join(
        f'<rect x="{plot_left:.1f}" y="{_y(min(b[1], hi)):.1f}" width="{plot_right - plot_left:.1f}" '
        f'height="{_y(max(b[0], lo)) - _y(min(b[1], hi)):.1f}" fill="{b[2]}"/>'
        f'<text x="{plot_right - 4:.1f}" y="{_y(min(b[1], hi)) + 12:.1f}" text-anchor="end" '
        f'font-size="10" font-weight="600" fill="{b[3]}">{_esc(b[4])}</text>'
        for b in cfg["bands"]
        if b[0] < hi and b[1] > lo
    )
    grid_svg = "".join(
        f'<line x1="{plot_left:.1f}" y1="{_y(t):.1f}" x2="{plot_right:.1f}" y2="{_y(t):.1f}" '
        f'stroke="#f0f0f0" stroke-width="1"/>'
        f'<text x="{plot_left - 6:.1f}" y="{_y(t) + 3:.1f}" text-anchor="end" '
        f'font-size="10" fill="#999">{t:g}{_esc(unit)}</text>'
        for t in ticks
    )
    x_labels_svg = "".join(
        f'<text x="{_x(i):.1f}" y="{plot_bottom + 16:.1f}" text-anchor="middle" '
        f'font-size="10" fill="#999">{_esc(_fmt_md(str(p.get("date", ""))))}</text>'
        for i, p in enumerate(points)
    )

    lines_svg = []
    legend_items = []
    for name, key, color in cfg["lines"]:
        pts = [(i, fv) for i, p in enumerate(points) if (fv := _to_float(p.get(key))) is not None]
        if pts:
            coords = " ".join(f"{_x(i):.1f},{_y(v):.1f}" for i, v in pts)
            dots = "".join(f'<circle cx="{_x(i):.1f}" cy="{_y(v):.1f}" r="2.5" fill="{color}"/>' for i, v in pts)
            lines_svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="2"/>{dots}')
        legend_items.append(
            f'<circle cx="0" cy="0" r="4" fill="{color}"/><text x="10" y="4" font-size="11" fill="#333">{_esc(name)}</text>'
        )
    legend_svg = "".join(
        f'<g transform="translate({plot_left + i * 90:.1f},{h - 8:.1f})">{item}</g>'
        for i, item in enumerate(legend_items)
    )

    avg = trend.get("avg")
    secondary_avg = trend.get("secondary_avg")
    if len(cfg["lines"]) > 1 and secondary_avg is not None:
        badge_svg = (
            f'<text x="{plot_right:.1f}" y="14" text-anchor="end" font-size="11" fill="#333">'
            f"{avg:g}{_esc(unit)} 평균 {cfg['lines'][0][0]}</text>"
            f'<text x="{plot_right:.1f}" y="28" text-anchor="end" font-size="11" fill="#333">'
            f"{secondary_avg:g}{_esc(unit)} 평균 {cfg['lines'][1][0]}</text>"
        )
    elif avg is not None:
        badge_svg = (
            f'<text x="{plot_right:.1f}" y="20" text-anchor="end" font-size="11" fill="#333">'
            f"{avg:g}{_esc(unit)} 평균</text>"
        )
    else:
        badge_svg = ""

    return (
        f'<svg width="100%" height="{h:g}" viewBox="0 0 {w:g} {h:g}" '
        f'preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">'
        f"{badge_svg}{bands_svg}{grid_svg}{''.join(lines_svg)}{x_labels_svg}{legend_svg}</svg>"
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
        if not any(isinstance(p, dict) and p.get("value") is not None for p in series):
            continue
        label = _METRIC_LABELS.get(t.get("metric", ""), (t.get("metric", ""), ""))[0]
        blocks.append(
            f'<div class="trend-card"><div class="trend-title">{_esc(label)} 추이</div>'
            f"{_trend_chart_svg(t)}</div>"
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
      .gauge-row { display: flex; gap: 16px; flex-wrap: wrap; }
      .gauge-card { text-align: center; flex: 1; min-width: 180px; }
      .trend-row { display: flex; flex-direction: column; gap: 16px; }
      .trend-card { text-align: center; width: 100%; }
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
    """리포트 dict → PDF bytes(+다운로드 파일명). 디스크/미디어 영속 없음."""

    async def build_bytes(self, report: dict[str, Any]) -> tuple[bytes, str]:
        """리포트 dict → (PDF bytes, 다운로드 파일명).

        PHI 보호: 파일을 디스크에 저장하지 않고 메모리상 바이트만 반환한다.
        호출하는 라우트가 인증된 사용자에게 attachment 로 즉시 내려보낸다.
        """
        html_str = build_report_html(report)
        pdf_bytes = await render_pdf_bytes(html_str)
        # year_month 는 사용자 쿼리에서 유래하므로 Content-Disposition 헤더에
        # 그대로 쓰지 않는다(개행/따옴표 인젝션 차단). 안전 문자만 남긴다.
        raw = str(report.get("year_month", "report"))
        safe = re.sub(r"[^0-9A-Za-z_-]", "", raw) or "report"
        filename = f"care_report_{safe}.pdf"
        return pdf_bytes, filename


__all__ = ["ReportPdfService", "build_report_html", "render_pdf_bytes"]
