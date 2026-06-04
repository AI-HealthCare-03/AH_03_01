"""만성질환 진료지침·서비스 가이드 4종을 RAGDocument(PGVector) 에 인덱싱한다.

대상 파일 (frontmatter 의 source_id → app/models/rag.py RAGDocument.source 로 매핑):
    KDA2025          — 2025 당뇨병 진료지침
    KSH2022          — 2022 고혈압 진료지침 5판
    DYS_GUIDELINE    — 이상지질혈증 치료지침 4판
    GUIDE            — 서비스 이용 가이드

파이프라인:
    1. python-frontmatter 로 파일 메타 + 본문 분리
    2. `## XXX_SEC_dddd — 제목` 또는 `## XXX_FIG_dddd — 제목` 정규식으로 섹션 분할
    3. 각 섹션의 `### Section Metadata` 블록을 dict 로 파싱
       - allowed_for_embedding == false 또는 use_restriction == excluded_from_rag 섹션 제외
    4. 임베딩 텍스트 = `### Content` + `### RAG 검색용 요약` + `### 검색 키워드` 결합
       (팀원 `ai_worker/rag/rag_chunker.py` 와 동일 로직)
    5. 500자/100자 overlap RecursiveCharacterTextSplitter 로 청크 분할 (10자 미만 제거)
    6. OpenAI text-embedding-3-small (1536d) 로 배치 임베딩 (배치 50, 3회 재시도)
    7. Tortoise ORM 으로 RAGDocument 적재

실행:
    uv run python -m scripts.rag.index_documents              # 기본 (이미 적재된 source 는 건너뜀)
    uv run python -m scripts.rag.index_documents --reset      # 같은 source_id 들의 기존 행 삭제 후 재적재
    uv run python -m scripts.rag.index_documents --dry-run    # 임베딩/적재 없이 청크 수만 리포트
    uv run python -m scripts.rag.index_documents --dump out.json  # 청크 전체를 JSON 파일로 덤프 (검수용, DB·API 미사용)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import frontmatter
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from tortoise import Tortoise

from app.core import config
from app.core.db.databases import TORTOISE_ORM
from app.models.rag import DocumentType, RAGDocument

# ─────────────────────────────────────────────
# 경로 / 대상 파일
# ─────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "RAG" / "final docs"

FILES: list[Path] = sorted(DOCS_DIR.glob("*.md"))

# ─────────────────────────────────────────────
# 청킹 / 임베딩 설정 (팀원 프로토타입과 동일 파라미터)
# ─────────────────────────────────────────────
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
MIN_CHUNK_LEN = 100

EMBEDDING_BATCH = 50
EMBEDDING_RETRY = 3
EMBEDDING_RETRY_DELAY = 5  # seconds

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", "。", ".", " ", ""],
)

# `## KDA2025_SEC_0001 — 당뇨병`, `## DYS_FIG_001 — ...`, `## GUIDE_SEC_001 — ...`,
# 그리고 `## KSOLA2022_SEC_0020_A — ...` (숫자 뒤 _접미사) 형태까지 모두 매칭.
SEC_HEADER = re.compile(
    r"^## ([A-Z][A-Z0-9_]+(?:_SEC_\d+(?:_[A-Z0-9]+)?|_FIG_\d+|FIG_\d+)) — (.+)$",
    re.MULTILINE,
)

# 서비스 가이드 + 챌린지 카탈로그는 GUIDELINE(의료 진료지침) 이 아니라 OTHER 로 적재하고
# metadata.doc_type 으로 구분한다. retrieve 의 source_type="service" 필터에서 둘 다 매치.
# (`DocumentType` enum 에 SERVICE_GUIDE 신규 값을 추가하려면 컬럼 길이도 ALTER 가 필요해
#  최소 변경 원칙상 OTHER + metadata + source 로 우회.)
SERVICE_GUIDE_SOURCES = {"GUIDE", "CHALLENGE_CATALOG"}

# scripts/rag/index_documents.py 에 추가할 TOPIC_MAPPING
# topic 값: diagnosis / medication / lifestyle / complication / risk / monitoring / service

TOPIC_MAPPING: dict[str, list[str]] = {

    # ══════════════════════════════════════════════════════
    # DM2025 — 2025 당뇨병 진료지침
    # ══════════════════════════════════════════════════════
    "DM2025_SEC_0003": ["diagnosis"],                          # Chapter 1. 당뇨병 분류 및 진단검사
    "DM2025_SEC_0004": ["diagnosis"],                          # 1-1. 당뇨병 진단 및 분류
    "DM2025_SEC_0005": ["diagnosis"],                          # 1-2. 당뇨병 선별검사
    "DM2025_SEC_0006": ["diagnosis"],                          # 1-3. 임신당뇨병 선별과 진단
    "DM2025_SEC_0007": ["lifestyle"],                          # Chapter 2. 2형당뇨병의 예방
    "DM2025_SEC_0008": ["monitoring"],                         # Chapter 3. 혈당조절 목표 및 저혈당 평가
    "DM2025_SEC_0009": ["monitoring"],                         # 3-1. 혈당조절 목표
    "DM2025_SEC_0010": ["monitoring", "medication"],           # 3-2. 저혈당 평가
    "DM2025_SEC_0011": ["monitoring"],                         # Chapter 4. 혈당조절의 모니터링
    "DM2025_SEC_0012": ["monitoring"],                         # 4-1. 혈당조절의 모니터링 및 평가
    "DM2025_SEC_0013": ["monitoring"],                         # 4-2. 연속혈당측정
    "DM2025_SEC_0015": ["lifestyle"],                          # 5-1. 당뇨병 자기관리
    "DM2025_SEC_0016": ["lifestyle", "medication"],            # 5-2. 저혈당관리
    "DM2025_SEC_0017": ["lifestyle"],                          # 5-3. 의학영양요법
    "DM2025_SEC_0018": ["lifestyle"],                          # 5-4. 운동요법
    "DM2025_SEC_0019": ["medication"],                         # Chapter 6. 당뇨병 약물치료
    "DM2025_SEC_0020": ["medication"],                         # 6-1. 1형당뇨병의 약물치료
    "DM2025_SEC_0021": ["medication"],                         # 6-2. 2형당뇨병의 약물치료
    "DM2025_SEC_0022": ["risk", "complication"],               # Chapter 7. 심혈관질환 위험관리
    "DM2025_SEC_0023": ["medication", "complication"],         # 7-1. 고혈압관리
    "DM2025_SEC_0024": ["medication", "complication"],         # 7-2. 지질관리
    "DM2025_SEC_0025": ["medication", "complication"],         # 7-3. 항혈소판제 사용
    "DM2025_SEC_0026": ["complication"],                       # Chapter 8. 당뇨병합병증관리
    "DM2025_SEC_0027": ["complication"],                       # 8-1. 당뇨병신장질환
    "DM2025_SEC_0028": ["complication"],                       # 8-2. 당뇨병신경병증 및 발관리
    "DM2025_SEC_0029": ["complication"],                       # 8-3. 당뇨병망막병증
    "DM2025_SEC_0030": ["complication", "medication"],         # 8-4. 당뇨병케토산증
    "DM2025_SEC_0031": ["complication", "lifestyle"],          # Chapter 9. 동반 대사질환관리
    "DM2025_SEC_0032": ["lifestyle", "complication"],          # 9-1. 비만 관리
    "DM2025_SEC_0033": ["complication"],                       # 9-2. 대사이상지방간질환
    "DM2025_SEC_0034": ["diagnosis", "medication"],            # Chapter 10. 소아청소년 당뇨병
    "DM2025_SEC_0035": ["medication", "lifestyle"],            # Chapter 11. 노인 당뇨병관리
    "DM2025_SEC_0036": ["medication"],                         # Chapter 12. 특수 상황
    "DM2025_SEC_0037": ["medication", "monitoring"],           # 12-1. 입원 및 중증질환 혈당관리
    "DM2025_SEC_0038": ["diagnosis", "medication"],            # 12-2. 당뇨병과 임신
    "DM2025_SEC_0039": ["lifestyle"],                          # 12-3. 백신접종
    "DM2025_FIG_001": ["diagnosis"],
    "DM2025_FIG_002": ["diagnosis"],
    "DM2025_FIG_003": ["diagnosis"],
    "DM2025_FIG_004": ["lifestyle", "monitoring"],
    "DM2025_FIG_006": ["medication"],
    "DM2025_FIG_007": ["medication"],
    "DM2025_FIG_008": ["medication"],
    "DM2025_FIG_009": ["medication"],
    "DM2025_FIG_010": ["medication", "complication"],
    "DM2025_FIG_011": ["complication"],
    "DM2025_FIG_012": ["complication"],
    "DM2025_FIG_013": ["complication"],
    "DM2025_FIG_014": ["complication"],
    "DM2025_FIG_015": ["complication"],
    "DM2025_FIG_016": ["complication", "medication"],

    # ══════════════════════════════════════════════════════
    # KSH2026 — 2026 고혈압 진료지침
    # ══════════════════════════════════════════════════════
    "KSH2026_SEC_0006": ["diagnosis"],                         # 1. 고혈압의 정의와 혈압의 분류
    "KSH2026_SEC_0007": ["risk"],                              # 2. 고혈압의 중요성
    "KSH2026_SEC_0008": ["risk"],                              # 3. 고혈압의 유병률
    "KSH2026_SEC_0009": ["monitoring"],                        # 4. 고혈압의 관리 현황
    "KSH2026_SEC_0010": ["lifestyle"],                         # 5. 소금 섭취와 고혈압
    "KSH2026_SEC_0011": ["risk", "lifestyle"],                 # 6. 대사증후군, 비만과 고혈압
    "KSH2026_SEC_0012": ["risk"],                              # 7. 심혈관질환 위험 점수
    "KSH2026_SEC_0013": ["diagnosis", "monitoring"],           # 8. 고혈압의 진단과 혈압 측정
    "KSH2026_SEC_0014": ["diagnosis"],                         # 8.1. 선별 검사와 진단
    "KSH2026_SEC_0015": ["diagnosis"],                         # 8.1.1. 선별 검사
    "KSH2026_SEC_0016": ["diagnosis"],                         # 8.1.2. 진단
    "KSH2026_SEC_0017": ["monitoring"],                        # 8.2. 혈압 측정 기기
    "KSH2026_SEC_0018": ["monitoring"],                        # 8.2.1. 혈압 측정 기기
    "KSH2026_SEC_0019": ["monitoring"],                        # 8.2.1.1. 커프형 혈압계
    "KSH2026_SEC_0020": ["monitoring"],                        # 8.2.1.2. 커프리스 혈압계
    "KSH2026_SEC_0021": ["monitoring"],                        # 8.2.2. 혈압계 검증
    "KSH2026_SEC_0022": ["monitoring"],                        # 8.3. 진료실혈압 측정
    "KSH2026_SEC_0023": ["monitoring"],                        # 8.3.1. 표준 혈압 측정법
    "KSH2026_SEC_0024": ["monitoring"],                        # 8.3.2. 특별 상황 혈압 측정
    "KSH2026_SEC_0025": ["monitoring"],                        # 8.3.2.1. 심방세동 혈압 측정
    "KSH2026_SEC_0026": ["monitoring", "diagnosis"],           # 8.3.2.2. 기립성 저혈압
    "KSH2026_SEC_0027": ["monitoring"],                        # 8.3.2.3. 임산부 혈압 측정
    "KSH2026_SEC_0028": ["monitoring"],                        # 8.3.3. 진료실자동혈압
    "KSH2026_SEC_0029": ["monitoring"],                        # 8.4. 진료실 밖 혈압 측정
    "KSH2026_SEC_0030": ["monitoring"],                        # 8.4.1. 활동혈압 측정
    "KSH2026_SEC_0031": ["monitoring"],                        # 8.4.2. 가정혈압 측정
    "KSH2026_SEC_0032": ["monitoring"],                        # 8.4.3. 활동/가정혈압 비교
    "KSH2026_SEC_0033": ["monitoring"],                        # 8.4.4. Dipping 패턴
    "KSH2026_SEC_0034": ["monitoring"],                        # 8.4.5. 혈압 변동성
    "KSH2026_SEC_0035": ["monitoring"],                        # 8.5. 중심동맥압 측정
    "KSH2026_SEC_0036": ["diagnosis", "monitoring"],           # 8.6. 고혈압 진단 기준
    "KSH2026_SEC_0037": ["diagnosis"],                         # 9. 환자의 평가
    "KSH2026_SEC_0038": ["diagnosis"],                         # 9.1. 증상 및 징후
    "KSH2026_SEC_0039": ["diagnosis"],                         # 9.2. 병력
    "KSH2026_SEC_0040": ["diagnosis"],                         # 9.3. 진찰
    "KSH2026_SEC_0041": ["diagnosis", "monitoring"],           # 9.4. 검사
    "KSH2026_SEC_0042": ["risk"],                              # 9.5. 심뇌혈관질환 위험인자
    "KSH2026_SEC_0043": ["risk"],                              # 9.6. 위험도 분류
    "KSH2026_SEC_0044": ["diagnosis"],                         # 9.7. 이차성 고혈압
    "KSH2026_SEC_0045": ["diagnosis"],                         # 9.7.1. 일차성 알도스테론증
    "KSH2026_SEC_0046": ["diagnosis"],                         # 9.7.2. 신동맥협착증
    "KSH2026_SEC_0047": ["diagnosis"],                         # 9.7.3. 기타
    "KSH2026_SEC_0048": ["medication"],                        # 10. 고혈압의 치료
    "KSH2026_SEC_0049": ["medication"],                        # 10.1. 치료 계획
    "KSH2026_SEC_0050": ["medication", "diagnosis"],           # 10.2. 치료 시작 혈압
    "KSH2026_SEC_0051": ["medication"],                        # 10.2.1. 고혈압 전단계
    "KSH2026_SEC_0052": ["medication"],                        # 10.2.2. 1기 고혈압
    "KSH2026_SEC_0053": ["medication"],                        # 10.2.3. 2기 고혈압
    "KSH2026_SEC_0054": ["medication"],                        # 10.2.4. 노인 고혈압
    "KSH2026_SEC_0055": ["medication", "monitoring"],          # 10.3. 목표혈압
    "KSH2026_SEC_0056": ["medication"],                        # 10.3.1. 노인 고혈압
    "KSH2026_SEC_0057": ["medication", "complication"],        # 10.3.2. 당뇨병 동반 고혈압
    "KSH2026_SEC_0058": ["medication", "complication"],        # 10.3.3. 뇌졸중 동반 고혈압
    "KSH2026_SEC_0059": ["medication", "complication"],        # 10.3.4. 만성콩팥병 동반 고혈압
    "KSH2026_SEC_0060": ["medication"],                        # 10.3.5. 치료 혈압 하한치
    "KSH2026_SEC_0061": ["medication", "monitoring"],          # 10.3.6. 측정 방식별 목표혈압
    "KSH2026_SEC_0062": ["lifestyle"],                         # 11. 비약물치료 및 생활요법
    "KSH2026_SEC_0063": ["lifestyle"],                         # 11.1. 체중 조절
    "KSH2026_SEC_0064": ["lifestyle"],                         # 11.2. 소금 섭취 제한
    "KSH2026_SEC_0065": ["lifestyle"],                         # 11.3. 절주
    "KSH2026_SEC_0066": ["lifestyle"],                         # 11.4. 운동
    "KSH2026_SEC_0067": ["lifestyle"],                         # 11.5. 금연
    "KSH2026_SEC_0068": ["lifestyle"],                         # 11.6. 건강한 식사요법
    "KSH2026_SEC_0069": ["lifestyle"],                         # 11.7. 마음 요법
    "KSH2026_SEC_0070": ["medication"],                        # 12. 약물 치료
    "KSH2026_SEC_0071": ["medication"],                        # 12.1. 고혈압약 처방 원칙
    "KSH2026_SEC_0072": ["medication"],                        # 12.1.1. 고혈압약 선택 원칙
    "KSH2026_SEC_0073": ["medication"],                        # 12.1.2. 고혈압약 선택
    "KSH2026_SEC_0074": ["medication"],                        # 12.2. 고혈압약 종류와 사용법
    "KSH2026_SEC_0075": ["medication"],                        # 12.2.1. 이뇨제
    "KSH2026_SEC_0076": ["medication"],                        # 12.2.2. 베타차단제
    "KSH2026_SEC_0077": ["medication"],                        # 12.2.3. 칼슘통로차단제
    "KSH2026_SEC_0078": ["medication"],                        # 12.2.4. 레닌-안지오텐신계 억제제
    "KSH2026_SEC_0079": ["medication"],                        # 12.2.5. ARNi
    "KSH2026_SEC_0080": ["medication"],                        # 12.2.6. 기타 약물
    "KSH2026_SEC_0081": ["medication"],                        # 12.3. 병용요법
    "KSH2026_SEC_0082": ["medication"],                        # 12.3.1. 단일제형복합요법
    "KSH2026_SEC_0083": ["medication"],                        # 12.4. 난치성 고혈압
    "KSH2026_SEC_0084": ["medication"],                        # 12.5. 콩팥교감신경차단술
    "KSH2026_SEC_0085": ["medication"],                        # 12.6. 고혈압약 감량/중단
    "KSH2026_SEC_0086": ["medication"],                        # 12.7. 기타 약물치료
    "KSH2026_SEC_0087": ["medication"],                        # 12.7.1. 항혈소판 요법
    "KSH2026_SEC_0088": ["medication"],                        # 12.7.2. 지질강하제
    "KSH2026_SEC_0089": ["medication", "monitoring"],          # 12.7.3. 혈당 조절
    "KSH2026_SEC_0090": ["monitoring"],                        # 12.8. 환자 모니터링
    "KSH2026_SEC_0091": ["medication"],                        # 12.9. 치료 지속성
    "KSH2026_SEC_0092": ["medication"],                        # 13. 상황별 고혈압 치료
    "KSH2026_SEC_0093": ["diagnosis", "monitoring"],           # 13.1. 백의고혈압/가면고혈압
    "KSH2026_SEC_0094": ["diagnosis"],                         # 13.1.1. 정의
    "KSH2026_SEC_0095": ["diagnosis", "medication"],           # 13.1.2. 백의고혈압
    "KSH2026_SEC_0096": ["diagnosis", "medication"],           # 13.1.3. 가면고혈압
    "KSH2026_SEC_0097": ["monitoring", "medication"],          # 13.2. 야간고혈압/아침고혈압
    "KSH2026_SEC_0098": ["risk", "medication"],                # 13.3. 대사증후군과 고혈압
    "KSH2026_SEC_0099": ["lifestyle", "medication"],           # 13.4. 비만과 고혈압
    "KSH2026_SEC_0100": ["medication", "complication"],        # 13.5. 당뇨병과 고혈압
    "KSH2026_SEC_0101": ["medication"],                        # 13.6. 노인 고혈압
    "KSH2026_SEC_0102": ["medication"],                        # 13.7. 젊은 연령 고혈압
    "KSH2026_SEC_0103": ["medication", "complication"],        # 13.8. 심장질환과 고혈압
    "KSH2026_SEC_0104": ["medication", "complication"],        # 13.8.1. 관상동맥질환
    "KSH2026_SEC_0105": ["medication", "complication"],        # 13.8.2. 심부전
    "KSH2026_SEC_0106": ["medication", "complication"],        # 13.8.3. 심방세동
    "KSH2026_SEC_0107": ["medication", "complication"],        # 13.8.4. 판막질환
    "KSH2026_SEC_0108": ["medication", "complication"],        # 13.8.4.1. 대동맥판 협착
    "KSH2026_SEC_0109": ["medication", "complication"],        # 13.8.4.2. 대동맥판 역류
    "KSH2026_SEC_0110": ["medication", "complication"],        # 13.8.4.3. 승모판 역류
    "KSH2026_SEC_0111": ["complication"],                      # 13.9. 혈관질환과 고혈압
    "KSH2026_SEC_0112": ["complication"],                      # 13.9.1. 경동맥 죽상동맥경화증
    "KSH2026_SEC_0113": ["complication"],                      # 13.9.2. 동맥경화증
    "KSH2026_SEC_0114": ["complication"],                      # 13.9.3. 말초혈관질환
    "KSH2026_SEC_0115": ["complication"],                      # 13.9.4. 대동맥 질환
    "KSH2026_SEC_0116": ["medication", "complication"],        # 13.10. 만성콩팥병과 고혈압
    "KSH2026_SEC_0117": ["complication", "medication"],        # 13.11. 뇌혈관질환과 고혈압
    "KSH2026_SEC_0118": ["medication", "complication"],        # 13.11.1. 급성기 허혈성 뇌졸중
    "KSH2026_SEC_0119": ["medication", "complication"],        # 13.11.2. 급성기 뇌출혈
    "KSH2026_SEC_0120": ["medication", "complication"],        # 13.11.3. 뇌졸중 이차 예방
    "KSH2026_SEC_0121": ["medication"],                        # 13.12. 발기부전과 고혈압
    "KSH2026_SEC_0122": ["medication", "diagnosis"],           # 13.13. 임신과 고혈압
    "KSH2026_SEC_0123": ["medication"],                        # 13.14. 여성과 고혈압
    "KSH2026_SEC_0124": ["complication", "medication"],        # 13.15. 수면무호흡증
    "KSH2026_SEC_0125": ["complication"],                      # 13.16. 인지기능 장애
    "KSH2026_SEC_0126": ["medication"],                        # 13.17. 고혈압성 응급
    "KSH2026_SEC_0127": ["lifestyle"],                         # 14. 환자 중심 치료
    "KSH2026_SEC_0128": ["lifestyle"],                         # 14.1. 환자 중심 진료
    "KSH2026_SEC_0129": ["monitoring", "lifestyle"],           # 14.2. 자가 혈압 측정
    "KSH2026_SEC_0130": ["medication", "lifestyle"],           # 14.3. 치료 지속성 향상
    "KSH2026_SEC_0131": ["lifestyle"],                         # 14.4. 다학제 관리
    "KSH2026_SEC_0132": ["lifestyle"],                         # 14.5. 환자 중심 관리 한계

    # ══════════════════════════════════════════════════════
    # KSOLA2022 — 이상지질혈증 진료지침
    # ══════════════════════════════════════════════════════
    "KSOLA2022_SEC_0002": ["risk"],                            # 제5판 변경 내용
    "KSOLA2022_SEC_0020_A": ["risk"],                          # 심혈관질환 위험요인
    "KSOLA2022_SEC_0020_C": ["risk"],                          # 심혈관질환 위험요인
    "KSOLA2022_SEC_0021": ["risk"],                            # 표 1-1. 위험요인 기여위험도
    "KSOLA2022_SEC_0022": ["risk"],                            # 표 1-2. 위험요인 비교위험도
    "KSOLA2022_SEC_0040": ["diagnosis"],                       # 진단 방법 및 기준
    "KSOLA2022_SEC_0051": ["risk"],                            # 표 2-3. 심혈관 위험인자
    "KSOLA2022_SEC_0060_A": ["monitoring"],                    # 경과 모니터링
    "KSOLA2022_SEC_0060_B": ["medication", "monitoring"],      # 스타틴 부작용 모니터링
    "KSOLA2022_SEC_0070": ["lifestyle"],                       # 식사요법
    "KSOLA2022_SEC_0071_A": ["lifestyle"],                     # 고콜레스테롤혈증 식사요법
    "KSOLA2022_SEC_0071_B": ["lifestyle"],                     # 포화지방산
    "KSOLA2022_SEC_0071_C": ["lifestyle"],                     # 탄수화물 및 식이섬유
    "KSOLA2022_SEC_0071_D": ["lifestyle"],                     # 불포화지방산
    "KSOLA2022_SEC_0071_E": ["lifestyle"],                     # 저HDL콜레스테롤혈증
    "KSOLA2022_SEC_0071_F": ["lifestyle"],                     # 우리나라 식사패턴
    "KSOLA2022_SEC_0073_A": ["lifestyle"],                     # 운동요법
    "KSOLA2022_SEC_0073_B": ["lifestyle"],                     # 운동의 혈중지질 개선 효과
    "KSOLA2022_SEC_0073_C": ["lifestyle", "medication"],       # 운동 고려사항
    "KSOLA2022_SEC_0073_D": ["lifestyle"],                     # 운동 증가 조언
    "KSOLA2022_SEC_0074": ["lifestyle"],                       # 운동 처방 요약
    "KSOLA2022_SEC_0075_A": ["lifestyle"],                     # 금연
    "KSOLA2022_SEC_0076": ["lifestyle"],                       # 절주
    "KSOLA2022_SEC_0084_F": ["medication"],                    # 스타틴 부작용
    "KSOLA2022_SEC_0105_A": ["complication", "medication"],    # 당뇨병과 이상지질혈증
    "KSOLA2022_SEC_0105_B": ["medication"],                    # 이상지질혈증 치료목표
    "KSOLA2022_SEC_0105_C": ["medication"],                    # 이상지질혈증 치료
    "KSOLA2022_SEC_0105_D": ["medication"],                    # 스타틴+오메가3 병용치료
    "KSOLA2022_SEC_0107_A": ["diagnosis", "lifestyle"],        # 소아청소년 이상지질혈증
    "KSOLA2022_SEC_0107_B": ["diagnosis"],                     # 소아청소년 진단
    "KSOLA2022_SEC_0107_C": ["medication", "lifestyle"],       # 소아청소년 치료
    "KSOLA2022_SEC_0107_D": ["lifestyle"],                     # 소아청소년 생활습관 개선
    "KSOLA2022_SEC_0108": ["diagnosis"],                       # 소아청소년 진단기준 표
    "KSOLA2022_SEC_0109": ["diagnosis"],                       # 소아청소년 선별검사 표
    "KSOLA2022_SEC_0110": ["risk"],                            # 소아청소년 위험인자 표
    "KSOLA2022_SEC_0111": ["medication"],                      # 이상지질혈증 약물 표
    "KSOLA2022_SEC_0117_A": ["diagnosis", "medication"],       # 임신 중 이상지질혈증
    "KSOLA2022_SEC_0117_B": ["complication"],                  # 임신 중 고지혈증
    "KSOLA2022_SEC_0117_C": ["complication"],                  # 거대아증
    "DYS_FIG_001": ["diagnosis"],
    "DYS_FIG_002": ["medication", "risk"],
    "DYS_FIG_003": ["medication", "risk"],
    "DYS_FIG_004": ["risk"],
    "DYS_FIG_005": ["lifestyle"],
    "DYS_FIG_005A": ["diagnosis", "medication"],
    "DYS_FIG_005B": ["diagnosis", "medication"],
    "DYS_FIG_007": ["diagnosis"],
    "DYS_FIG_012": ["diagnosis"],
}


def _get_topics(section_id: str) -> list[str]:
    """섹션 ID로 topic 목록 조회. 매핑 없으면 빈 리스트."""
    return TOPIC_MAPPING.get(section_id, [])

# M-6 sanity 허용 figure 접두사 — 각 진료지침이 본문에 다른 자료의 figure 를 인용하는
# 경우가 있어 source_id prefix 외에 추가 허용 (silent 매치 경고 false positive 방지).
_KNOWN_FIGURE_PREFIXES = ("DYS_FIG_", "HTN_FIG_", "DM_FIG_", "CHALL_SEC_", "CHALL_FIG_")


# ─────────────────────────────────────────────
# 청킹 헬퍼
# ─────────────────────────────────────────────
def parse_section_metadata(meta_block: str) -> dict[str, str]:
    """`### Section Metadata` 블록의 bullet 리스트 → dict."""
    result: dict[str, str] = {}
    for raw in meta_block.splitlines():
        line = raw.strip()
        if not line.startswith("- "):
            continue
        line = line[2:]
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        result[key.strip()] = val.strip().strip("`").strip('"').strip("'")
    return result


def split_section_text(text: str) -> list[tuple[int, int, str]]:
    """(chunk_index, chunk_total, chunk_text) 튜플 목록을 돌려준다."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= CHUNK_SIZE:
        return [(0, 1, text)]
    pieces = splitter.split_text(text)
    total = len(pieces)
    return [(i, total, p) for i, p in enumerate(pieces)]


def build_embedding_text(block: str) -> str:
    """팀원과 동일하게 Content + RAG요약 + 키워드 를 합쳐 임베딩 입력 텍스트로 만든다."""
    parts: list[str] = []

    content_match = re.search(r"### Content\s*\n(.*?)(?=### |\Z)", block, re.DOTALL)
    if content_match:
        parts.append(content_match.group(1).strip())

    rag_match = re.search(r"#{3,5}.*?RAG 검색용 요약.*?\n(.*?)(?=#{3,5}|\Z)", block, re.DOTALL)
    if rag_match:
        parts.append("[RAG요약] " + rag_match.group(1).strip())

    kw_match = re.search(r"#{3,5}.*?검색 키워드.*?\n(.*?)(?=#{3,5}|\Z)", block, re.DOTALL)
    if kw_match:
        keywords = [
            line.strip().lstrip("- ").strip()
            for line in kw_match.group(1).strip().splitlines()
            if line.strip().startswith("-")
        ]
        if keywords:
            parts.append("[키워드] " + ", ".join(keywords))

    return "\n\n".join(p for p in parts if p)


def parse_file(filepath: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:  # noqa: C901 — 평면 파싱 분기
    """파일 1개를 파싱해 (file_meta, chunks) 를 돌려준다."""
    if not filepath.exists():
        print(f"  ⚠️  파일 없음, 건너뜀: {filepath}")
        return {}, []

    post = frontmatter.load(filepath)
    file_meta = dict(post.metadata)
    body = post.content
    matches = list(SEC_HEADER.finditer(body))

    # M-6 sanity: section_id 가 frontmatter.source_id 의 prefix(예: "KSOLA2022")로 시작하거나
    # 의료 도메인의 알려진 figure 접두사 인지 sample 검증. 정규식 확장으로 의도 외 패턴이
    # 매치되면 즉시 경고 (silent 매치 방지).
    # 알려진 figure 접두사: 각 진료지침이 본문에 다른 자료의 figure 를 인용하는 경우가 있음.
    source_id_str = str(file_meta.get("source_id") or "")
    if source_id_str and matches:
        sample_ids = [m.group(1) for m in matches[:5]]
        for sid in sample_ids:
            if not (sid.startswith(source_id_str) or sid.startswith(_KNOWN_FIGURE_PREFIXES)):
                print(f"  ⚠️  [{filepath.name}] 의심 section_id 매치: {sid} (source_id={source_id_str})")

    chunks: list[dict[str, Any]] = []
    skipped = 0

    for idx, match in enumerate(matches):
        section_id = match.group(1)
        section_title = match.group(2).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        block = body[start:end]

        sec_meta: dict[str, str] = {}
        meta_match = re.search(r"### Section Metadata\s*\n(.*?)(?=### |\Z)", block, re.DOTALL)
        if meta_match:
            sec_meta = parse_section_metadata(meta_match.group(1))

        # 임베딩 제외 필터 (팀원과 동일)
        if sec_meta.get("allowed_for_embedding", "True").lower() == "false":
            skipped += 1
            continue
        if sec_meta.get("use_restriction", "") == "excluded_from_rag":
            skipped += 1
            continue

        full_text = build_embedding_text(block)
        if not full_text or len(full_text.strip()) < MIN_CHUNK_LEN:
            skipped += 1
            continue

        for chunk_index, chunk_total, chunk_text in split_section_text(full_text):
            if len(chunk_text.strip()) < MIN_CHUNK_LEN:
                continue
            chunks.append(
                {
                    "section_id": section_id,
                    "section_title": section_title,
                    "chunk_index": chunk_index,
                    "chunk_total": chunk_total,
                    "chunk_text": chunk_text,
                    "sec_meta": sec_meta,
                }
            )

    print(f"  ✅ [{filepath.name}] 섹션 {len(matches)}개 (제외 {skipped}) → 청크 {len(chunks)}개")
    return file_meta, chunks


# ─────────────────────────────────────────────
# 임베딩
# ─────────────────────────────────────────────
def _safe_err_repr(e: BaseException) -> str:
    """OpenAI SDK 예외에서 API key prefix/요청 body 가 그대로 stdout/로그에 새는 걸 막는다.

    예외 타입명과 메시지 첫 줄 일부만 노출 (요청 ID/헤더/페이로드 마스킹).
    """
    head = str(e).splitlines()[0] if str(e) else ""
    return f"{type(e).__name__}: {head[:120]}"


def embed_batch(client: OpenAI, texts: list[str]) -> list[list[float]]:
    last_err: Exception | None = None
    for attempt in range(EMBEDDING_RETRY):
        try:
            resp = client.embeddings.create(model=config.OPENAI_EMBEDDING_MODEL, input=texts)
            return [item.embedding for item in resp.data]
        except Exception as e:  # noqa: BLE001 — OpenAI SDK 의 다양한 예외 통합 처리
            last_err = e
            print(f"  ⚠️  임베딩 오류 (시도 {attempt + 1}/{EMBEDDING_RETRY}): {_safe_err_repr(e)}")
            if attempt < EMBEDDING_RETRY - 1:
                time.sleep(EMBEDDING_RETRY_DELAY)
    raise RuntimeError(f"임베딩 {EMBEDDING_RETRY}회 실패: {_safe_err_repr(last_err) if last_err else 'unknown'}")


# ─────────────────────────────────────────────
# DB 적재
# ─────────────────────────────────────────────
def doc_type_for(source_id: str) -> DocumentType:
    if source_id in SERVICE_GUIDE_SOURCES:
        return DocumentType.OTHER
    return DocumentType.GUIDELINE


def truncate(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value if len(value) <= limit else value[: limit - 1] + "…"


async def load_chunks_to_db(
    source_id: str,
    file_meta: dict[str, Any],
    chunks: list[dict[str, Any]],
    embeddings: list[list[float]],
) -> int:
    objects: list[RAGDocument] = []
    for chunk, vec in zip(chunks, embeddings, strict=True):
        sec_meta = chunk["sec_meta"]
        topics = _get_topics(chunk["section_id"])
        metadata = {
            # 파일/문서 레벨
            "source_id": source_id,
            "source_title": file_meta.get("source_title"),
            "source_file": file_meta.get("source_file"),
            "disease": file_meta.get("disease"),
            "disease_ko": file_meta.get("disease_ko"),
            "language_original": file_meta.get("language_original"),
            "documentation_type": file_meta.get("documentation_type") or file_meta.get("doc_type"),
            "doc_type": file_meta.get("doc_type")
            or ("service_guide" if source_id in SERVICE_GUIDE_SOURCES else "guideline"),
            # 섹션 레벨
            "section_id": chunk["section_id"],
            "section_title": chunk["section_title"],
            "chunk_total": chunk["chunk_total"],
            "source_pages": sec_meta.get("source_pages"),
            "content_hash": sec_meta.get("content_hash"),
            "translation_status": sec_meta.get("translation_status"),
            "topics": topics if topics else None,  # 빈 리스트는 None으로 
        }
        # None 값 제거 (검색 필터/디버깅 가독성)
        metadata = {k: v for k, v in metadata.items() if v is not None}

        objects.append(
            RAGDocument(
                document_type=doc_type_for(source_id),
                source=source_id,
                title=truncate(chunk["section_title"], 200),
                chunk_index=chunk["chunk_index"],
                chunk_text=chunk["chunk_text"],
                embedding=vec,
                metadata=metadata,
                is_active=True,
            )
        )

    # bulk_create 는 PGVector 컬럼도 잘 처리 (asyncpg 연결마다 register_vector 등록됨)
    await RAGDocument.bulk_create(objects, batch_size=100)
    return len(objects)


# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────
def dump_chunks_to_json(
    parsed: list[tuple[str, dict[str, Any], list[dict[str, Any]]]],
    out_path: Path,
) -> None:
    """검수용: 모든 청크를 풍부한 메타와 함께 JSON 으로 직렬화한다 (임베딩/DB 미사용)."""
    payload: list[dict[str, Any]] = []
    for source_id, file_meta, chunks in parsed:
        for c in chunks:
            payload.append(
                {
                    "source_id": source_id,
                    "section_id": c["section_id"],
                    "section_title": c["section_title"],
                    "chunk_index": c["chunk_index"],
                    "chunk_total": c["chunk_total"],
                    "char_len": len(c["chunk_text"]),
                    "disease": file_meta.get("disease"),
                    "doc_type": file_meta.get("doc_type") or file_meta.get("documentation_type"),
                    "source_pages": c["sec_meta"].get("source_pages"),
                    "content_hash": c["sec_meta"].get("content_hash"),
                    "translation_status": c["sec_meta"].get("translation_status"),
                    "document_type_target": doc_type_for(source_id).value,
                    "chunk_text": c["chunk_text"],
                }
            )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 간단 통계 리포트
    lengths = [p["char_len"] for p in payload]
    print(f"\n  📄 청크 덤프 → {out_path}")
    print(
        f"  총 청크: {len(payload)}개 | 길이(글자): min={min(lengths)} / max={max(lengths)} / avg={sum(lengths) // len(lengths)}"
    )
    print("  소스별 청크 수:")
    from collections import Counter

    for src, cnt in sorted(Counter(p["source_id"] for p in payload).items()):
        print(f"    {src:18s}: {cnt}")


async def main(  # noqa: C901 — 일회성 ops 스크립트, 단계별 분기를 한 함수에 두는 게 가독성에 유리
    reset: bool,
    dry_run: bool,
    dump_path: Path | None,
    assume_yes: bool = False,
) -> int:
    if not config.OPENAI_API_KEY and not dry_run and dump_path is None:
        print("❌ OPENAI_API_KEY 가 비어 있습니다. envs/.local.env 확인 후 다시 실행하세요.", file=sys.stderr)
        return 2

    print("=" * 60)
    print("  RAG 인덱싱 — final docs → RAGDocument (PGVector 1536d)")
    print(f"  dry_run={dry_run} reset={reset} dump={dump_path}")
    print("=" * 60)

    # 1) 파싱 + 청킹
    parsed: list[tuple[str, dict[str, Any], list[dict[str, Any]]]] = []
    for fpath in FILES:
        file_meta, chunks = parse_file(fpath)
        if not chunks:
            continue
        source_id = str(file_meta.get("source_id") or "UNKNOWN")
        parsed.append((source_id, file_meta, chunks))

    total_chunks = sum(len(c) for _, _, c in parsed)
    print(f"\n  총 청크: {total_chunks}개 (소스 {len(parsed)}개)")

    if dump_path is not None:
        dump_chunks_to_json(parsed, dump_path)
        # 덤프는 검수 목적이므로 임베딩/적재 없이 여기서 종료
        return 0

    if dry_run:
        print("\n  --dry-run: 임베딩/적재 없이 종료")
        return 0

    if total_chunks == 0:
        print("  ⚠️  적재할 청크가 없습니다.")
        return 0

    # 2) Tortoise 초기화 (pgvector 코덱은 풀의 init 콜백으로 자동 등록 — databases.py 참조)
    await Tortoise.init(config=TORTOISE_ORM)

    try:
        # 3) reset 옵션: 같은 source 의 기존 행 삭제 (운영 DB 오인 보호)
        sources_in_run = [s for s, _, _ in parsed]
        if reset:
            existing_count = await RAGDocument.filter(source__in=sources_in_run).count()
            print(
                f"\n  ⚠️  --reset: DB={config.DB_HOST}/{config.DB_NAME} 의 "
                f"source {sources_in_run} 총 {existing_count}행을 삭제합니다."
            )
            if assume_yes:
                print("  (--yes 로 확인 생략)")
            else:
                answer = input("  진행하시려면 'yes' 입력: ").strip().lower()
                if answer != "yes":
                    print("  취소되었습니다.")
                    return 1
            deleted = await RAGDocument.filter(source__in=sources_in_run).delete()
            print(f"  ✅ {deleted}행 삭제 완료")
        else:
            # 기본 동작: 이미 적재된 source 는 건너뜀 (중복 적재 방지)
            existing = await RAGDocument.filter(source__in=sources_in_run).distinct().values_list("source", flat=True)
            existing_set = set(existing)
            if existing_set:
                print(f"\n  이미 적재된 source 건너뜀: {sorted(existing_set)}")
                parsed = [t for t in parsed if t[0] not in existing_set]
                if not parsed:
                    print("  → 적재할 새 source 없음 (재적재하려면 --reset).")
                    return 0

        # 4) 임베딩 + 적재 (소스 단위로 처리)
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        grand_total = 0
        for source_id, file_meta, chunks in parsed:
            print(f"\n  ── {source_id}: {len(chunks)}청크 임베딩/적재 ──")
            embeddings: list[list[float]] = []
            for batch_start in range(0, len(chunks), EMBEDDING_BATCH):
                batch = chunks[batch_start : batch_start + EMBEDDING_BATCH]
                texts = [c["chunk_text"] for c in batch]
                vecs = embed_batch(client, texts)
                if vecs and len(vecs[0]) != 1536:
                    raise RuntimeError(f"임베딩 차원이 1536 이 아님: {len(vecs[0])} — 모델/컬럼 차원을 확인하세요.")
                embeddings.extend(vecs)
                print(
                    f"    배치 {batch_start // EMBEDDING_BATCH + 1}"
                    f" / {(len(chunks) + EMBEDDING_BATCH - 1) // EMBEDDING_BATCH}"
                    f" — 누적 {len(embeddings)}/{len(chunks)}"
                )

            inserted = await load_chunks_to_db(source_id, file_meta, chunks, embeddings)
            grand_total += inserted
            print(f"    ✅ {source_id}: {inserted}행 적재")

        # 5) BM25 인덱스 무효화 — 같은 프로세스 안에서만 즉시 효과. FastAPI 워커는
        # 별도 프로세스라 자동 반영되지 않으므로, 운영 워커 재시작 또는 admin
        # reload 신호가 별도로 필요하다는 점을 경고로 남긴다.
        from app.services.ml.retrieval import invalidate_bm25_index

        invalidate_bm25_index()

        # 6) 리포트 — 이번 실행에서 적재된 source 들의 누적 행 수
        print("\n" + "=" * 60)
        print(f"  🎉 적재 완료: 이번 실행 {grand_total}행")
        print("  소스별 누적 행 수 (rag_documents 전체):")
        for src in sorted({s for s, _, _ in parsed}):
            cnt = await RAGDocument.filter(source=src).count()
            print(f"    {src:18s}: {cnt}행")
        print("=" * 60)
        print("  ⚠️  운영 FastAPI 워커는 BM25 인덱스를 부팅 시점에 메모리에 적재하므로")
        print("     본 인덱싱 결과를 즉시 반영하려면 워커 재시작이 필요합니다.")
        return 0
    finally:
        await Tortoise.close_connections()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reset", action="store_true", help="대상 source 의 기존 행 삭제 후 재적재")
    p.add_argument("--dry-run", action="store_true", help="임베딩/적재 없이 청크 통계만 출력")
    p.add_argument(
        "--dump",
        type=Path,
        metavar="OUT.json",
        help="청크 전체를 JSON 파일로 덤프 (검수용, 임베딩/DB 미사용)",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="--reset 의 확인 프롬프트를 건너뛴다 (CI/자동화용)",
    )
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sys.exit(
        asyncio.run(
            main(
                reset=args.reset,
                dry_run=args.dry_run,
                dump_path=args.dump,
                assume_yes=args.yes,
            )
        )
    )
