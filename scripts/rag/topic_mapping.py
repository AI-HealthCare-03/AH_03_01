"""
섹션 ID → topic 매핑 테이블
======================================
MD 파일이 추가/변경되면 이 파일만 수정
index_documents.py 는 이 파일을 import해서 사용

topic 값:
    diagnosis   — 진단 기준·선별검사·분류
    medication  — 약물치료·처방·부작용
    lifestyle   — 식사·운동·금연·절주·체중관리
    complication — 합병증·동반질환
    risk        — 위험도 평가·위험인자
    monitoring  — 혈압/혈당 측정·추적관리·모니터링
    service     — 서비스 이용안내·기능설명·FAQ
    challenge   — 챌린지 참여·인증·보상·추천
"""

from __future__ import annotations

# ══════════════════════════════════════════════════════════════
# DM2025 — 2025 당뇨병 진료지침 (source_id: DM_GUIDELINE_2025)
# ══════════════════════════════════════════════════════════════
_DM2025: dict[str, list[str]] = {
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
    # figures
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
}

# ══════════════════════════════════════════════════════════════
# KSH2026 — 2026 고혈압 진료지침 (source_id: KSH2026)
# ══════════════════════════════════════════════════════════════
_KSH2026: dict[str, list[str]] = {
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
}

# ══════════════════════════════════════════════════════════════
# KSOLA2022 — 이상지질혈증 진료지침 (source_id: KSOLA2022)
# ══════════════════════════════════════════════════════════════
_KSOLA2022: dict[str, list[str]] = {
    "KSOLA2022_SEC_0002": ["risk"],
    "KSOLA2022_SEC_0020_A": ["risk"],
    "KSOLA2022_SEC_0020_C": ["risk"],
    "KSOLA2022_SEC_0021": ["risk"],
    "KSOLA2022_SEC_0022": ["risk"],
    "KSOLA2022_SEC_0040": ["diagnosis"],
    "KSOLA2022_SEC_0051": ["risk"],
    "KSOLA2022_SEC_0060_A": ["monitoring"],
    "KSOLA2022_SEC_0060_B": ["medication", "monitoring"],
    "KSOLA2022_SEC_0070": ["lifestyle"],
    "KSOLA2022_SEC_0071_A": ["lifestyle"],
    "KSOLA2022_SEC_0071_B": ["lifestyle"],
    "KSOLA2022_SEC_0071_C": ["lifestyle"],
    "KSOLA2022_SEC_0071_D": ["lifestyle"],
    "KSOLA2022_SEC_0071_E": ["lifestyle"],
    "KSOLA2022_SEC_0071_F": ["lifestyle"],
    "KSOLA2022_SEC_0073_A": ["lifestyle"],
    "KSOLA2022_SEC_0073_B": ["lifestyle"],
    "KSOLA2022_SEC_0073_C": ["lifestyle", "medication"],
    "KSOLA2022_SEC_0073_D": ["lifestyle"],
    "KSOLA2022_SEC_0074": ["lifestyle"],
    "KSOLA2022_SEC_0075_A": ["lifestyle"],
    "KSOLA2022_SEC_0076": ["lifestyle"],
    "KSOLA2022_SEC_0084_F": ["medication"],
    "KSOLA2022_SEC_0105_A": ["complication", "medication"],
    "KSOLA2022_SEC_0105_B": ["medication"],
    "KSOLA2022_SEC_0105_C": ["medication"],
    "KSOLA2022_SEC_0105_D": ["medication"],
    "KSOLA2022_SEC_0107_A": ["diagnosis", "lifestyle"],
    "KSOLA2022_SEC_0107_B": ["diagnosis"],
    "KSOLA2022_SEC_0107_C": ["medication", "lifestyle"],
    "KSOLA2022_SEC_0107_D": ["lifestyle"],
    "KSOLA2022_SEC_0108": ["diagnosis"],
    "KSOLA2022_SEC_0109": ["diagnosis"],
    "KSOLA2022_SEC_0110": ["risk"],
    "KSOLA2022_SEC_0111": ["medication"],
    "KSOLA2022_SEC_0117_A": ["diagnosis", "medication"],
    "KSOLA2022_SEC_0117_B": ["complication"],
    "KSOLA2022_SEC_0117_C": ["complication"],
    # figures
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

# ══════════════════════════════════════════════════════════════
# GUIDE — 서비스 이용 가이드 (source_id: GUIDE)
# ══════════════════════════════════════════════════════════════
_GUIDE: dict[str, list[str]] = {
    "GUIDE_SEC_001": ["service"],                              # 1-1. 서비스 목적
    "GUIDE_SEC_002": ["service"],                              # 1-2. 주요 대상 사용자
    "GUIDE_SEC_003": ["service"],                              # 1-3. 제공 기능 요약
    "GUIDE_SEC_004": ["service"],                              # 2-1. 회원 관리
    "GUIDE_SEC_005": ["service", "challenge"],                 # 2-2. 챌린지 참여
    "GUIDE_SEC_006": ["service"],                              # 2-3. 건강 데이터 기록
    "GUIDE_SEC_007": ["service"],                              # 2-4. 질병 예측 및 시각화
    "GUIDE_SEC_008": ["service"],                              # 2-5. 보상 시스템
    "GUIDE_SEC_008A": ["service"],                             # 2-5-1. 경험치(EXP) 시스템
    "GUIDE_SEC_008B": ["service"],                             # 2-5-2. 캐릭터 레벨 구간
    "GUIDE_SEC_008C": ["service"],                             # 2-5-3. 경험치 어뷰징 방지
    "GUIDE_SEC_008D": ["service"],                             # 2-5-4. 리더보드 점수 vs 누적 EXP
    "GUIDE_SEC_009": ["service"],                              # 2-6. 알림 기능
    "GUIDE_SEC_010": ["service"],                              # 2-7. 커뮤니티
    "GUIDE_SEC_011": ["service"],                              # 2-8. 고객 지원
    "GUIDE_SEC_012": ["service"],                              # 2-9. 챗봇 기능
    "GUIDE_SEC_013": ["service"],                              # 3-1. 어떤 데이터를 사용하는지
    "GUIDE_SEC_014": ["service"],                              # 3-2. 예측 결과 의미
    "GUIDE_SEC_015": ["service"],                              # 3-3. 주의사항
    "GUIDE_SEC_016": ["service"],                              # 3-4. 의료 진단 대체 불가 안내
    "GUIDE_SEC_017": ["service"],                              # 4-1. 로그인 문제
    "GUIDE_SEC_018": ["service"],                              # 4-2. 건강 데이터 관련
    "GUIDE_SEC_019": ["service", "challenge"],                 # 4-3. 챌린지 인증
    "GUIDE_SEC_020": ["service", "challenge"],                 # 4-4. 포인트 지급
    "GUIDE_SEC_020A": ["service"],                             # 4-5. 경험치(EXP) 관련
    "GUIDE_SEC_021": ["service"],                              # 4-6. 예측 결과 관련
    "GUIDE_SEC_022": ["service"],                              # 5-1. 개인정보 처리
    "GUIDE_SEC_023": ["service"],                              # 5-2. 커뮤니티 이용 규칙
    "GUIDE_SEC_024": ["service", "challenge"],                 # 5-3. 허위 인증 제한
    "GUIDE_SEC_025": ["service"],                              # 5-4. AI 결과 책임 범위
    "GUIDE_SEC_026": ["service"],                              # 5-5. 웨어러블 기기 연동 제한
    "GUIDE_SEC_027": ["service"],                              # 5-6. 서비스 운영 정책
}

# ══════════════════════════════════════════════════════════════
# CHALLENGE_CATALOG — 챌린지 카탈로그 (source_id: CHALLENGE_CATALOG)
# ══════════════════════════════════════════════════════════════
_CHALLENGE_CATALOG: dict[str, list[str]] = {
    "CHALL_SEC_0001": ["challenge", "service"],                # 챌린지 시스템 개요 및 참여 방식
    "CHALL_SEC_0002": ["challenge", "service"],                # 챌린지 보상 체계
    "CHALL_SEC_0003": ["challenge", "service"],                # 챌린지 인증 방식 개요
    "CHALL_SEC_0004": ["challenge", "lifestyle"],              # 걷기 챌린지
    "CHALL_SEC_0005": ["challenge", "lifestyle"],              # 러닝 챌린지
    "CHALL_SEC_0006": ["challenge", "lifestyle"],              # 자전거 챌린지
    "CHALL_SEC_0007": ["challenge", "lifestyle"],              # 근력 운동 챌린지
    "CHALL_SEC_0008": ["challenge", "lifestyle"],              # 수영 챌린지
    "CHALL_SEC_0009": ["challenge", "lifestyle"],              # 기타 운동 챌린지
    "CHALL_SEC_0010": ["challenge", "lifestyle"],              # 물 마시기 챌린지
    "CHALL_SEC_0011": ["challenge", "lifestyle"],              # 수면 챌린지
    "CHALL_SEC_0012": ["challenge", "lifestyle"],              # 식단 챌린지
    "CHALL_SEC_0013": ["challenge", "lifestyle"],              # 체중 관리 챌린지
    "CHALL_SEC_0014": ["challenge", "lifestyle"],              # 금연 챌린지
    "CHALL_SEC_0015": ["challenge", "lifestyle"],              # 금주 챌린지
    "CHALL_SEC_0016": ["challenge", "lifestyle"],              # 명상 챌린지
    "CHALL_SEC_0017": ["challenge", "lifestyle", "complication"],  # 질환 관리 챌린지 — 당뇨발
    "CHALL_SEC_0018": ["challenge", "service"],                # 그룹 챌린지 운영 규칙
    "CHALL_SEC_0019": ["challenge", "service"],                # 챌린지 실패 방지권
    "CHALL_SEC_0020": ["challenge", "service"],                # 챌린지 주간/월간 요약
    "CHALL_SEC_0021": ["challenge", "lifestyle", "risk"],      # 위험도 기반 챌린지 추천 로직
    "CHALL_SEC_0022": ["challenge", "service"],                # 활동량 리더보드
}

# ══════════════════════════════════════════════════════════════
# 전체 통합 매핑
# ══════════════════════════════════════════════════════════════
TOPIC_MAPPING: dict[str, list[str]] = {
    **_DM2025,
    **_KSH2026,
    **_KSOLA2022,
    **_GUIDE,
    **_CHALLENGE_CATALOG,
}


def _get_topics(section_id: str) -> list[str]:
    """섹션 ID로 topic 목록 조회. 매핑 없으면 빈 리스트."""
    return TOPIC_MAPPING.get(section_id, [])