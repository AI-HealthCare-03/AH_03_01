"""
섹션 ID → topic 매핑 테이블
======================================
MD 파일이 추가/변경되면 이 파일만 수정
index_documents.py 는 이 파일을 import해서 사용

topic 값:
    diagnosis    — 진단 기준·선별검사·분류
    medication   — 약물치료·처방·부작용
    lifestyle    — 복합 생활습관 (자기관리·수면·스트레스·환자중심치료 등 단일 서브토픽으로 분류 불가한 경우)
    exercise     — 운동요법 (유산소·근력·신체활동 권고)
    diet         — 식사요법·영양 (저염·저지방·저당·식이패턴 포함)
    weight       — 체중/비만 관리
    smoking      — 금연
    alcohol      — 절주
    complication — 합병증·동반질환
    risk         — 위험도 평가·위험인자
    monitoring   — 혈압/혈당 측정·추적관리·모니터링
    service      — 서비스 이용안내·기능설명·FAQ
    challenge    — 챌린지 참여·인증·보상·추천

lifestyle 서브토픽 분류 기준:
    exercise  → 운동/신체활동 방법·효과·처방이 섹션의 핵심일 때
    diet      → 식품 선택·영양소·식사패턴·염분 제한이 핵심일 때
    weight    → 체중 감량·비만도 측정·BMI 기준이 핵심일 때
    smoking   → 흡연 영향·금연 방법이 핵심일 때
    alcohol   → 음주 영향·절주 방법이 핵심일 때
    lifestyle → 위 5개에 명확히 속하지 않거나 2개 이상 복합인 경우
"""

from __future__ import annotations

# ══════════════════════════════════════════════════════════════
# KDA2025 — 2025 당뇨병 진료지침 (source_id: KDA2025)
# ══════════════════════════════════════════════════════════════
_KDA2025: dict[str, list[str]] = {
    # 총론·개요
    "KDA2025_SEC_0001": ["diagnosis"],                          # 당뇨병 (개요)
    "KDA2025_SEC_0002": ["lifestyle"],                          # 당뇨인의 권익 옹호
    "KDA2025_SEC_0003": ["lifestyle"],                          # 학교 환경에서의 당뇨병관리
    "KDA2025_SEC_0004": ["lifestyle"],                          # 당뇨병과 운전
    "KDA2025_SEC_0005": ["diagnosis"],                          # 2025 당뇨병 진료지침 요약
    "KDA2025_SEC_0018": ["diagnosis"],                          # 근거수준과 권고범위
    "KDA2025_SEC_0019": ["diagnosis"],                          # 목차

    # I. 진단·분류
    "KDA2025_SEC_0006": ["diagnosis"],                          # 3-1. 당뇨병의 진단 및 분류
    "KDA2025_SEC_0007": ["diagnosis"],                          # 3-2. 당뇨병 선별검사
    "KDA2025_SEC_0020": ["diagnosis"],                          # I. 당뇨병 분류 및 진단검사
    "KDA2025_SEC_0021": ["diagnosis"],                          # 공복혈당장애·경구포도당내성검사
    "KDA2025_SEC_0022": ["diagnosis"],                          # 그림 1-1.1 당대사이상 분류
    "KDA2025_SEC_0023": ["diagnosis"],                          # 당화혈색소(A1C, HbA1c)
    "KDA2025_SEC_0024": ["diagnosis"],                          # 당뇨병의 분류
    "KDA2025_SEC_0025": ["diagnosis"],                          # 이득(편익) — 진단
    "KDA2025_SEC_0026": ["diagnosis"],                          # 참고문헌 — 진단
    "KDA2025_SEC_0027": ["diagnosis"],                          # 1-2. 당뇨병 선별검사
    "KDA2025_SEC_0028": ["diagnosis"],                          # 권고2. 선별검사
    "KDA2025_SEC_0029": ["diagnosis"],                          # 그림 1-2.1 연령별 NNS
    "KDA2025_SEC_0030": ["diagnosis"],                          # 이득(편익) — 선별
    "KDA2025_SEC_0031": ["diagnosis"],                          # 권고3. 선별 후 추적관찰
    "KDA2025_SEC_0032": ["diagnosis"],                          # 권고4. 임신당뇨병 출산 후 검사
    "KDA2025_SEC_0033": ["diagnosis"],                          # 참고문헌 — 선별
    "KDA2025_SEC_0034": ["diagnosis"],                          # 1-3. 임신당뇨병 선별과 진단
    "KDA2025_SEC_0035": ["diagnosis"],                          # 권고1. 임신 초기 검사
    "KDA2025_SEC_0036": ["diagnosis"],                          # 권고2. 임신 24-28주 선별
    "KDA2025_SEC_0037": ["diagnosis"],                          # 참고문헌 — 임신당뇨병
    "KDA2025_SEC_0038": ["diagnosis"],                          # 그림 1-3.1 임신 시 당뇨병 진단

    # II. 당뇨병 예방
    "KDA2025_SEC_0039": ["lifestyle"],                          # II. 2형당뇨병의 예방
    "KDA2025_SEC_0040": ["diet"],                               # 권고3. 당뇨전단계 식사요법
    "KDA2025_SEC_0041": ["medication"],                         # 권고6. 메트포민 당뇨 예방
    "KDA2025_SEC_0042": ["lifestyle"],                          # 표 2.1 생활습관교정 근거
    "KDA2025_SEC_0043": ["lifestyle"],                          # 표 2.2 장기 관찰연구 근거
    "KDA2025_SEC_0044": ["lifestyle"],                          # 표 2.3 ICT 기반 보조수단
    "KDA2025_SEC_0045": ["medication"],                         # 표 2.4 약물중재 근거
    "KDA2025_SEC_0046": ["lifestyle"],                          # 참고문헌 — 예방

    # III. 혈당 목표·저혈당
    "KDA2025_SEC_0047": ["monitoring"],                         # III. 혈당조절 목표 및 저혈당 예방
    "KDA2025_SEC_0048": ["monitoring"],                         # 이득(편익) — 혈당조절
    "KDA2025_SEC_0049": ["monitoring"],                         # 위해 — 혈당조절
    "KDA2025_SEC_0050": ["monitoring"],                         # 권고3. 1형당뇨병 HbA1c 목표
    "KDA2025_SEC_0051": ["monitoring"],                         # 권고4. 혈당 목표 개별화
    "KDA2025_SEC_0052": ["monitoring"],                         # 권고5. TIR 목표
    "KDA2025_SEC_0053": ["monitoring"],                         # 참고문헌 — 혈당 목표
    "KDA2025_SEC_0054": ["monitoring", "medication"],           # 3-2. 저혈당 평가
    "KDA2025_SEC_0055": ["monitoring"],                         # 표 3-2.1 저혈당 단계별 수준
    "KDA2025_SEC_0056": ["monitoring"],                         # 권고2. 저혈당·인지기능
    "KDA2025_SEC_0057": ["monitoring"],                         # 권고3. 저혈당무감지증 평가
    "KDA2025_SEC_0058": ["monitoring", "risk"],                 # 표 3-2.2 중증저혈당 위험인자
    "KDA2025_SEC_0059": ["monitoring", "medication"],           # 그림 3-2.1 저혈당 대처법
    "KDA2025_SEC_0060": ["monitoring"],                         # 참고문헌 — 저혈당

    # IV. 혈당 모니터링
    "KDA2025_SEC_0008": ["monitoring"],                         # 3-4-1. 혈당조절의 모니터링 및 평가
    "KDA2025_SEC_0061": ["monitoring"],                         # IV. 혈당조절의 모니터링
    "KDA2025_SEC_0062": ["monitoring"],                         # 권고1. 당화혈색소 측정
    "KDA2025_SEC_0063": ["monitoring"],                         # 표 4-1.1 당화혈색소·평균혈당 관계
    "KDA2025_SEC_0064": ["monitoring"],                         # 권고2. 자기혈당측정 (1)
    "KDA2025_SEC_0065": ["monitoring"],                         # 권고2. 자기혈당측정 (2)
    "KDA2025_SEC_0066": ["monitoring"],                         # 참고문헌 — 모니터링
    "KDA2025_SEC_0067": ["monitoring"],                         # 4-2. 연속혈당측정
    "KDA2025_SEC_0068": ["monitoring"],                         # 권고1. CGM core metrics
    "KDA2025_SEC_0069": ["monitoring"],                         # 권고2. CGM 교육
    "KDA2025_SEC_0070": ["monitoring"],                         # 권고3. 1형당뇨병 CGM
    "KDA2025_SEC_0071": ["monitoring"],                         # 권고4. 2형당뇨병 다회인슐린 CGM
    "KDA2025_SEC_0072": ["monitoring"],                         # 권고5. 기저인슐린 CGM
    "KDA2025_SEC_0073": ["monitoring"],                         # 권고6. 간헐스캔 CGM
    "KDA2025_SEC_0074": ["monitoring"],                         # CGM 임상 근거
    "KDA2025_SEC_0075": ["monitoring"],                         # 권고7. 임신 1형당뇨 CGM
    "KDA2025_SEC_0076": ["monitoring"],                         # 표 4-2.1 CGM core metrics 기준
    "KDA2025_SEC_0077": ["monitoring"],                         # 표 4-2.2 환자군별 TIR 목표
    "KDA2025_SEC_0078": ["monitoring"],                         # 그림 4-2.1 AGP 보고서
    "KDA2025_SEC_0079": ["monitoring"],                         # 참고문헌 — CGM

    # V. 자기관리
    "KDA2025_SEC_0009": ["lifestyle"],                          # 3-5-1. 당뇨병 자기관리
    "KDA2025_SEC_0080": ["lifestyle"],                          # V. 포괄적인 자기관리
    "KDA2025_SEC_0081": ["lifestyle"],                          # 이득(편익) — 자기관리
    "KDA2025_SEC_0082": ["lifestyle"],                          # 자기관리교육 효과 근거
    "KDA2025_SEC_0083": ["lifestyle"],                          # 권고4. 다학제 자기관리교육
    "KDA2025_SEC_0084": ["lifestyle"],                          # 참고문헌 — 자기관리
    "KDA2025_SEC_0085": ["monitoring", "medication"],           # 5-2. 저혈당관리
    "KDA2025_SEC_0086": ["monitoring"],                         # 당뇨병 발생 위험도 감소효과
    "KDA2025_SEC_0087": ["monitoring", "medication"],           # 권고2. 저혈당 대처 방법
    "KDA2025_SEC_0088": ["medication"],                         # 권고3. 글루카곤 처방
    "KDA2025_SEC_0089": ["complication"],                       # 미세혈관합병증 발생
    "KDA2025_SEC_0090": ["diagnosis"],                          # 당뇨병 발생
    "KDA2025_SEC_0091": ["monitoring"],                         # 참고문헌 — 저혈당관리

    # 5-3. 의학영양요법
    "KDA2025_SEC_0010": ["diet"],                               # 3-5-3. 의학영양요법
    "KDA2025_SEC_0092": ["diet"],                               # 5-3. 의학영양요법 권고 목록
    "KDA2025_SEC_0093": ["diet"],                               # 권고1. 개별화 영양요법
    "KDA2025_SEC_0094": ["diet", "weight"],                     # 권고2. 체중 감량·에너지 제한
    "KDA2025_SEC_0095": ["diet"],                               # 권고3. 식사패턴 개별화
    "KDA2025_SEC_0096": ["diet"],                               # 권고4. 탄수화물 섭취 제한
    "KDA2025_SEC_0097": ["diet"],                               # 권고5. 식이섬유 섭취
    "KDA2025_SEC_0098": ["diet"],                               # 권고6. 첨가당·가당음료 제한
    "KDA2025_SEC_0099": ["diet", "complication"],               # 권고7. 단백질·신장질환
    "KDA2025_SEC_0100": ["diet"],                               # 권고8. 포화지방·트랜스지방 제한
    "KDA2025_SEC_0101": ["diet"],                               # 권고9. 나트륨 2,300mg 이내
    "KDA2025_SEC_0102": ["diet"],                               # 권고10. 미량영양소 보충제
    "KDA2025_SEC_0103": ["alcohol"],                            # 권고11. 음주·금주 권고
    "KDA2025_SEC_0104": ["diet"],                               # 참고문헌 — 의학영양요법

    # 5-4. 운동요법
    "KDA2025_SEC_0105": ["exercise"],                           # 5-4. 운동요법 권고 목록
    "KDA2025_SEC_0106": ["exercise"],                           # 권고1-3. 운동 개별화·사전 평가
    "KDA2025_SEC_0107": ["exercise", "monitoring"],             # 표 5-4.1 운동 전 혈당 대처
    "KDA2025_SEC_0108": ["exercise", "monitoring"],             # 권고5-9. 유산소·저항운동 (운동 전 혈당 대처 포함)
    "KDA2025_SEC_0109": ["exercise"],                           # 참고문헌 — 운동요법

    # 6-1. 1형당뇨병 약물치료
    "KDA2025_SEC_0011": ["medication"],                         # 3-6-1. 1형당뇨병의 약물치료
    "KDA2025_SEC_0110": ["medication"],                         # 6-1. 1형당뇨병 약물치료 권고 목록
    "KDA2025_SEC_0111": ["medication", "lifestyle"],            # 권고1-3. 인슐린 교육·소아청소년
    "KDA2025_SEC_0112": ["medication"],                         # 권고4. 저혈당무감지증 교육
    "KDA2025_SEC_0113": ["medication", "monitoring"],           # 권고5. 다회인슐린/펌프 CGM
    "KDA2025_SEC_0114": ["medication"],                         # 참고문헌 — 1형당뇨병 약물

    # 6-2. 2형당뇨병 약물치료
    "KDA2025_SEC_0012": ["medication"],                         # 3-6-2. 2형당뇨병의 약물치료
    "KDA2025_SEC_0115": ["medication"],                         # 6-2. 2형당뇨병 약물치료 권고 요약
    "KDA2025_SEC_0116": ["medication", "lifestyle"],            # 권고1. 진단 즉시 생활습관교정
    "KDA2025_SEC_0117": ["medication", "complication"],         # 권고2. 동반질환 고려 약물 선택
    "KDA2025_SEC_0118": ["medication"],                         # 권고3. 고혈당 인슐린치료
    "KDA2025_SEC_0119": ["medication"],                         # 권고4-1. 단독/병용요법 시작
    "KDA2025_SEC_0120": ["medication"],                         # 권고4-2. 초기 병용요법
    "KDA2025_SEC_0121": ["medication"],                         # 권고5. 복약순응도 확인
    "KDA2025_SEC_0122": ["medication"],                         # 권고6. 목표 미달 병용요법
    "KDA2025_SEC_0123": ["medication"],                         # 권고7. 주사제 포함 치료
    "KDA2025_SEC_0124": ["medication"],                         # 권고7-1. GLP-1 우선
    "KDA2025_SEC_0125": ["medication"],                         # 권고7-2. GLP-1·기저인슐린 병용
    "KDA2025_SEC_0126": ["medication"],                         # 권고7-3. 인슐린강화요법
    "KDA2025_SEC_0127": ["medication", "complication"],         # 권고8. 심부전 SGLT2억제제
    "KDA2025_SEC_0128": ["medication", "complication"],         # 권고9. 알부민뇨 SGLT2억제제
    "KDA2025_SEC_0129": ["medication", "complication"],         # 권고10. 죽상경화 GLP-1/SGLT2
    "KDA2025_SEC_0130": ["medication"],                         # 표 6-2.1 혈당강하제 종류·특징
    "KDA2025_SEC_0131": ["medication", "complication"],         # 표 6-2.2 SGLT2 outcome trials
    "KDA2025_SEC_0132": ["medication", "complication"],         # 표 6-2.3 GLP-1 outcome trials
    "KDA2025_SEC_0133": ["medication"],                         # 표 6-2.4 인슐린 종류·작용시간
    "KDA2025_SEC_0134": ["medication"],                         # 표 6-2.5 GLP-1·기저인슐린 비교
    "KDA2025_SEC_0135": ["medication"],                         # 표 6-2.6 병용 vs GLP-1 단독
    "KDA2025_SEC_0136": ["medication"],                         # 표 6-2.7 병용 vs 기저인슐린 단독
    "KDA2025_SEC_0137": ["medication"],                         # 표 6-2.8 인슐린 시작·용량조절
    "KDA2025_SEC_0138": ["medication", "complication"],         # 표 6-2.9 심부전 약물치료
    "KDA2025_SEC_0139": ["medication"],                         # 그림 6-2.1 약물치료 알고리듬
    "KDA2025_SEC_0140": ["medication", "complication"],         # 그림 6-2.2 신장기능별 약물 조절
    "KDA2025_SEC_0141": ["medication"],                         # 그림 6-2.3 메트포민·조영제 주의
    "KDA2025_SEC_0142": ["medication"],                         # 참고문헌 — 2형당뇨병 약물

    # 7. 심혈관 위험관리
    "KDA2025_SEC_0143": ["risk", "complication"],               # 심혈관질환 위험관리 챕터
    "KDA2025_SEC_0013": ["medication", "complication"],         # 3-7. 고혈압관리
    "KDA2025_SEC_0144": ["medication", "complication"],         # 7-1. 고혈압관리 권고 목록
    "KDA2025_SEC_0145": ["medication", "monitoring"],           # 7-1. 혈압 측정·목표·생활습관교정
    "KDA2025_SEC_0146": ["medication"],                         # 7-1. 항고혈압제 선택·병용요법
    "KDA2025_SEC_0147": ["medication", "complication"],         # 7-1. 그림·참고문헌
    "KDA2025_SEC_0014": ["medication", "complication"],         # 3-8. 지질관리
    "KDA2025_SEC_0148": ["medication", "complication"],         # 7-2. 지질관리 권고 목록
    "KDA2025_SEC_0149": ["medication", "monitoring"],           # 7-2. LDL 조절목표 결정
    "KDA2025_SEC_0150": ["medication"],                         # 7-2. LDL 수치별 근거
    "KDA2025_SEC_0151": ["medication"],                         # 7-2. 스타틴·에제티미브·PCSK9
    "KDA2025_SEC_0152": ["medication", "complication"],         # 7-2. 고중성지방혈증
    "KDA2025_SEC_0153": ["medication", "complication"],         # 7-3. 항혈소판제

    # 8. 합병증 관리
    "KDA2025_SEC_0154": ["complication"],                       # 당뇨병합병증관리 챕터
    "KDA2025_SEC_0155": ["complication"],                       # 8-1. 당뇨병신장질환 권고 목록
    "KDA2025_SEC_0156": ["complication", "monitoring"],         # 8-1. 신장질환 진단·혈당·혈압·단백질
    "KDA2025_SEC_0157": ["complication", "medication"],         # 8-1. ACE억제제/ARB/SGLT2/finerenone
    "KDA2025_SEC_0158": ["complication"],                       # 8-1. 그림·참고문헌
    "KDA2025_SEC_0159": ["complication"],                       # 8-2. 당뇨병신경병증·발관리
    "KDA2025_SEC_0160": ["complication"],                       # 8-3. 당뇨병망막병증
    "KDA2025_SEC_0161": ["complication", "medication"],         # 8-4. 당뇨병케토산증·고삼투질상태

    # 9. 동반 대사질환
    "KDA2025_SEC_0162": ["complication", "weight"],             # 동반 대사질환관리 챕터
    "KDA2025_SEC_0015": ["weight"],                             # 3-9. 비만 관리
    "KDA2025_SEC_0163": ["weight", "medication"],               # 9-1. 비만관리 권고
    "KDA2025_SEC_0016": ["complication"],                       # 3-10. 대사이상지방간질환 관리
    "KDA2025_SEC_0164": ["complication", "diet"],               # 9-2. 대사이상지방간질환 관리

    # 10. 소아청소년
    "KDA2025_SEC_0017": ["diagnosis", "medication"],            # 3-11. 소아청소년의 2형당뇨병관리
    "KDA2025_SEC_0165": ["diagnosis"],                          # 소아청소년 챕터 표지
    "KDA2025_SEC_0166": ["diagnosis", "medication"],            # 10. 소아청소년 2형당뇨병 권고

    # 11. 노인당뇨
    "KDA2025_SEC_0167": ["medication"],                         # 노인당뇨 챕터 표지
    "KDA2025_SEC_0168": ["medication", "monitoring"],           # 11. 노인당뇨병 권고

    # 12. 특수 상황
    "KDA2025_SEC_0169": ["medication"],                         # 특수 상황 챕터 표지
    "KDA2025_SEC_0170": ["monitoring", "medication"],           # 12-1. 입원 혈당관리 권고 목록
    "KDA2025_SEC_0171": ["monitoring", "medication"],           # 12-1. 입원 혈당관리 권고 상세
    "KDA2025_SEC_0172": ["diagnosis", "monitoring"],            # 12-2. 당뇨병과 임신 권고 목록
    "KDA2025_SEC_0173": ["monitoring", "medication"],           # 12-2. 임신 혈당·생활습관·인슐린
    "KDA2025_SEC_0174": ["medication", "diagnosis"],            # 12-2. 그림·참고문헌
    "KDA2025_SEC_0175": ["lifestyle"],                          # 12-3. 백신접종

    # 진료지침 개발·연혁
    "KDA2025_SEC_0176": ["diagnosis"],                          # 진료지침 개발과정 챕터
    "KDA2025_SEC_0177": ["diagnosis"],                          # 진료지침 개발 본문
    "KDA2025_SEC_0178": ["diagnosis"],                          # 개발그룹 명단
    "KDA2025_SEC_0179": ["diagnosis"],                          # 진료지침 연혁 챕터
    "KDA2025_SEC_0180": ["diagnosis"],                          # 진료지침 연혁 본문
    "KDA2025_SEC_0181": ["diagnosis"],                          # 역대 위원 명단
}

# ══════════════════════════════════════════════════════════════
# KSH2026 — 2026 고혈압 진료지침 (source_id: KSH2026)
# ══════════════════════════════════════════════════════════════
_KSH2026: dict[str, list[str]] = {
    # 총론·개요
    "KSH2026_SEC_0001": ["diagnosis"],                          # 머리말
    "KSH2026_SEC_0002": ["diagnosis"],                          # 인사말
    "KSH2026_SEC_0003": ["diagnosis"],                          # 신구 대비표 — 신규 추가 항목
    "KSH2026_SEC_0004": ["diagnosis"],                          # 신구 대비표 — 변경 항목
    "KSH2026_SEC_0005": ["diagnosis"],                          # 근거 수준 및 권고 등급 정의
    "KSH2026_SEC_0006": ["diagnosis"],                          # 1. 고혈압의 정의와 혈압의 분류
    "KSH2026_SEC_0007": ["risk"],                               # 2. 고혈압의 중요성
    "KSH2026_SEC_0008": ["risk"],                               # 3. 고혈압의 유병률
    "KSH2026_SEC_0009": ["monitoring"],                         # 4. 고혈압의 관리 현황
    "KSH2026_SEC_0010": ["diet"],                               # 5. 소금 섭취와 고혈압
    "KSH2026_SEC_0011": ["risk", "weight"],                     # 6. 대사증후군, 비만과 고혈압
    "KSH2026_SEC_0012": ["risk"],                               # 7. 심혈관질환 위험 점수

    # 진단·혈압 측정
    "KSH2026_SEC_0015": ["diagnosis"],                          # 8.1.1. 선별 검사
    "KSH2026_SEC_0016": ["diagnosis"],                          # 8.1.2. 진단
    "KSH2026_SEC_0018": ["monitoring"],                         # 8.2.1. 혈압 측정 기기
    "KSH2026_SEC_0019": ["monitoring"],                         # 8.2.1.1. 커프형 혈압계
    "KSH2026_SEC_0020": ["monitoring"],                         # 8.2.1.2. 커프리스 혈압계
    "KSH2026_SEC_0021": ["monitoring"],                         # 8.2.2. 혈압계 검증
    "KSH2026_SEC_0022": ["monitoring"],                         # 8.3. 진료실혈압 측정
    "KSH2026_SEC_0023": ["monitoring"],                         # 8.3.1. 표준 혈압 측정법
    "KSH2026_SEC_0024": ["monitoring"],                         # 8.3.2. 특별 상황 혈압 측정
    "KSH2026_SEC_0025": ["monitoring"],                         # 8.3.2.1. 심방세동 혈압 측정
    "KSH2026_SEC_0026": ["monitoring", "diagnosis"],            # 8.3.2.2. 기립성 저혈압
    "KSH2026_SEC_0027": ["monitoring"],                         # 8.3.2.3. 임산부 혈압 측정
    "KSH2026_SEC_0028": ["monitoring"],                         # 8.3.3. 진료실자동혈압
    "KSH2026_SEC_0029": ["monitoring"],                         # 8.4. 진료실 밖 혈압 측정
    "KSH2026_SEC_0030": ["monitoring"],                         # 8.4.1. 활동혈압 측정
    "KSH2026_SEC_0031": ["monitoring"],                         # 8.4.2. 가정혈압 측정
    "KSH2026_SEC_0032": ["monitoring"],                         # 8.4.3. 활동/가정혈압 비교
    "KSH2026_SEC_0033": ["monitoring"],                         # 8.4.4. Dipping 패턴
    "KSH2026_SEC_0034": ["monitoring"],                         # 8.4.5. 혈압 변동성
    "KSH2026_SEC_0035": ["monitoring"],                         # 8.5. 중심동맥압 측정
    "KSH2026_SEC_0036": ["diagnosis", "monitoring"],            # 8.6. 고혈압 진단 기준

    # 환자 평가
    "KSH2026_SEC_0037": ["diagnosis"],                          # 9. 환자의 평가
    "KSH2026_SEC_0038": ["diagnosis"],                          # 9.1. 증상 및 징후
    "KSH2026_SEC_0039": ["diagnosis"],                          # 9.2. 병력
    "KSH2026_SEC_0040": ["diagnosis"],                          # 9.3. 진찰
    "KSH2026_SEC_0041": ["diagnosis", "monitoring"],            # 9.4. 검사
    "KSH2026_SEC_0042": ["risk"],                               # 9.5. 심뇌혈관질환 위험인자
    "KSH2026_SEC_0043": ["risk"],                               # 9.6. 위험도 분류
    "KSH2026_SEC_0044": ["diagnosis"],                          # 9.7. 이차성 고혈압
    "KSH2026_SEC_0045": ["diagnosis"],                          # 9.7.1. 일차성 알도스테론증
    "KSH2026_SEC_0046": ["diagnosis"],                          # 9.7.2. 신동맥협착증
    "KSH2026_SEC_0047": ["diagnosis"],                          # 9.7.3. 기타

    # 치료 목표
    "KSH2026_SEC_0048": ["medication"],                         # 10. 고혈압의 치료
    "KSH2026_SEC_0049": ["medication"],                         # 10.1. 치료 계획
    "KSH2026_SEC_0050": ["medication", "diagnosis"],            # 10.2. 치료 시작 혈압
    "KSH2026_SEC_0051": ["medication"],                         # 10.2.1. 고혈압 전단계
    "KSH2026_SEC_0052": ["medication"],                         # 10.2.2. 1기 고혈압
    "KSH2026_SEC_0053": ["medication"],                         # 10.2.3. 2기 고혈압
    "KSH2026_SEC_0054": ["medication"],                         # 10.2.4. 노인 고혈압
    "KSH2026_SEC_0055": ["medication", "monitoring"],           # 10.3. 목표혈압
    "KSH2026_SEC_0056": ["medication"],                         # 10.3.1. 노인 고혈압
    "KSH2026_SEC_0057": ["medication", "complication"],         # 10.3.2. 당뇨병 동반 고혈압
    "KSH2026_SEC_0058": ["medication", "complication"],         # 10.3.3. 뇌졸중 동반 고혈압
    "KSH2026_SEC_0059": ["medication", "complication"],         # 10.3.4. 만성콩팥병 동반 고혈압
    "KSH2026_SEC_0060": ["medication"],                         # 10.3.5. 치료 혈압 하한치
    "KSH2026_SEC_0061": ["medication", "monitoring"],           # 10.3.6. 측정 방식별 목표혈압

    # 생활요법
    "KSH2026_SEC_0062": ["lifestyle"],                          # 11. 비약물치료 및 생활요법 (총론)
    "KSH2026_SEC_0063": ["weight"],                             # 11.1. 체중 조절
    "KSH2026_SEC_0064": ["diet"],                               # 11.2. 소금 섭취 제한
    "KSH2026_SEC_0065": ["alcohol"],                            # 11.3. 절주
    "KSH2026_SEC_0066": ["exercise"],                           # 11.4. 운동
    "KSH2026_SEC_0067": ["smoking"],                            # 11.5. 금연
    "KSH2026_SEC_0068": ["diet"],                               # 11.6. 건강한 식사요법
    "KSH2026_SEC_0069": ["lifestyle"],                          # 11.7. 마음 요법

    # 약물치료
    "KSH2026_SEC_0070": ["medication"],                         # 12. 약물 치료
    "KSH2026_SEC_0071": ["medication"],                         # 12.1. 고혈압약 처방 원칙
    "KSH2026_SEC_0072": ["medication"],                         # 12.1.1. 고혈압약 선택 원칙
    "KSH2026_SEC_0073": ["medication"],                         # 12.1.2. 고혈압약 선택
    "KSH2026_SEC_0074": ["medication"],                         # 12.2. 고혈압약 종류와 사용법
    "KSH2026_SEC_0075": ["medication"],                         # 12.2.1. 이뇨제
    "KSH2026_SEC_0076": ["medication"],                         # 12.2.2. 베타차단제
    "KSH2026_SEC_0077": ["medication"],                         # 12.2.3. 칼슘통로차단제
    "KSH2026_SEC_0078": ["medication"],                         # 12.2.4. 레닌-안지오텐신계 억제제
    "KSH2026_SEC_0079": ["medication"],                         # 12.2.5. ARNi
    "KSH2026_SEC_0080": ["medication"],                         # 12.2.6. 기타 약물
    "KSH2026_SEC_0081": ["medication"],                         # 12.3. 병용요법
    "KSH2026_SEC_0082": ["medication"],                         # 12.3.1. 단일제형복합요법
    "KSH2026_SEC_0083": ["medication"],                         # 12.4. 난치성 고혈압
    "KSH2026_SEC_0084": ["medication"],                         # 12.5. 콩팥교감신경차단술
    "KSH2026_SEC_0085": ["medication"],                         # 12.6. 고혈압약 감량/중단
    "KSH2026_SEC_0086": ["medication"],                         # 12.7. 기타 약물치료
    "KSH2026_SEC_0087": ["medication"],                         # 12.7.1. 항혈소판 요법
    "KSH2026_SEC_0088": ["medication"],                         # 12.7.2. 지질강하제
    "KSH2026_SEC_0089": ["medication", "monitoring"],           # 12.7.3. 혈당 조절
    "KSH2026_SEC_0090": ["monitoring"],                         # 12.8. 환자 모니터링
    "KSH2026_SEC_0091": ["medication"],                         # 12.9. 치료 지속성

    # 상황별 고혈압
    "KSH2026_SEC_0093": ["diagnosis", "monitoring"],            # 13.1. 백의고혈압/가면고혈압
    "KSH2026_SEC_0094": ["diagnosis"],                          # 13.1.1. 정의
    "KSH2026_SEC_0095": ["diagnosis", "medication"],            # 13.1.2. 백의고혈압
    "KSH2026_SEC_0096": ["diagnosis", "medication"],            # 13.1.3. 가면고혈압
    "KSH2026_SEC_0097": ["monitoring", "medication"],           # 13.2. 야간/아침고혈압
    "KSH2026_SEC_0098": ["risk", "medication"],                 # 13.3. 대사증후군과 고혈압
    "KSH2026_SEC_0099": ["weight", "medication"],               # 13.4. 비만과 고혈압
    "KSH2026_SEC_0100": ["medication", "complication"],         # 13.5. 당뇨병과 고혈압
    "KSH2026_SEC_0101": ["medication"],                         # 13.6. 노인 고혈압
    "KSH2026_SEC_0102": ["medication"],                         # 13.7. 젊은 연령 고혈압
    "KSH2026_SEC_0103": ["medication", "complication"],         # 13.8. 심장질환과 고혈압
    "KSH2026_SEC_0104": ["medication", "complication"],         # 13.8.1. 관상동맥질환
    "KSH2026_SEC_0105": ["medication", "complication"],         # 13.8.2. 심부전
    "KSH2026_SEC_0106": ["medication", "complication"],         # 13.8.3. 심방세동
    "KSH2026_SEC_0107": ["medication", "complication"],         # 13.8.4. 판막질환
    "KSH2026_SEC_0108": ["medication", "complication"],         # 13.8.4.1. 대동맥판 협착
    "KSH2026_SEC_0109": ["medication", "complication"],         # 13.8.4.2. 대동맥판 역류
    "KSH2026_SEC_0110": ["medication", "complication"],         # 13.8.4.3. 승모판 역류
    "KSH2026_SEC_0112": ["complication"],                       # 13.9.1. 경동맥 죽상동맥경화증
    "KSH2026_SEC_0113": ["complication"],                       # 13.9.2. 동맥경화증
    "KSH2026_SEC_0114": ["complication"],                       # 13.9.3. 말초혈관질환
    "KSH2026_SEC_0115": ["complication"],                       # 13.9.4. 대동맥 질환
    "KSH2026_SEC_0116": ["medication", "complication"],         # 13.10. 만성콩팥병과 고혈압
    "KSH2026_SEC_0117": ["complication", "medication"],         # 13.11. 뇌혈관질환과 고혈압
    "KSH2026_SEC_0118": ["medication", "complication"],         # 13.11.1. 급성기 허혈성 뇌졸중
    "KSH2026_SEC_0119": ["medication", "complication"],         # 13.11.2. 급성기 뇌출혈
    "KSH2026_SEC_0120": ["medication", "complication"],         # 13.11.3. 뇌졸중 이차 예방
    "KSH2026_SEC_0121": ["medication"],                         # 13.12. 발기부전과 고혈압
    "KSH2026_SEC_0122": ["medication", "diagnosis"],            # 13.13. 임신과 고혈압
    "KSH2026_SEC_0123": ["medication"],                         # 13.14. 여성과 고혈압
    "KSH2026_SEC_0124": ["complication", "medication"],         # 13.15. 수면무호흡증
    "KSH2026_SEC_0125": ["complication"],                       # 13.16. 인지기능 장애
    "KSH2026_SEC_0126": ["medication"],                         # 13.17. 고혈압성 응급

    # 환자 중심 치료
    "KSH2026_SEC_0128": ["lifestyle"],                          # 14.1. 환자 중심 진료
    "KSH2026_SEC_0129": ["monitoring", "lifestyle"],            # 14.2. 자가 혈압 측정
    "KSH2026_SEC_0130": ["medication", "lifestyle"],            # 14.3. 치료 지속성 향상
    "KSH2026_SEC_0131": ["lifestyle"],                          # 14.4. 다학제 관리
    "KSH2026_SEC_0132": ["lifestyle"],                          # 14.5. 환자 중심 관리 한계

    # 그림
    "KSH2026_FIG_001": ["diagnosis"],
    "KSH2026_FIG_002": ["risk"],
    "KSH2026_FIG_003": ["risk"],
    "KSH2026_FIG_004": ["risk"],
    "KSH2026_FIG_005": ["risk"],
    "KSH2026_FIG_006": ["risk"],
    "KSH2026_FIG_007": ["diagnosis"],
    "KSH2026_FIG_008": ["monitoring"],
    "KSH2026_FIG_009": ["monitoring"],
    "KSH2026_FIG_010": ["monitoring"],
    "KSH2026_FIG_011": ["monitoring"],
    "KSH2026_FIG_012": ["diagnosis"],
    "KSH2026_FIG_013": ["medication"],
    "KSH2026_FIG_014": ["medication", "monitoring"],
    "KSH2026_FIG_015": ["lifestyle"],
    "KSH2026_FIG_016": ["medication", "risk"],
    "KSH2026_FIG_017": ["medication"],
    "KSH2026_FIG_018": ["medication", "diagnosis"],
    "KSH2026_FIG_019": ["diagnosis", "monitoring"],
    "KSH2026_FIG_020": ["medication", "complication"],
}

# ══════════════════════════════════════════════════════════════
# KSLA2022 — 이상지질혈증 진료지침 (source_id: KSLA2022)
# 주의: DB 저장 section_id 는 "KSLA2022_SEC_" (O 없음). 이전 "KSOLA2022_SEC_" 키는 미매핑.
# ══════════════════════════════════════════════════════════════
_KSLA2022: dict[str, list[str]] = {
    # ── 서문 ──────────────────────────────────────────────────
    "KSLA2022_SEC_0001": ["risk"],                                    # 인사말
    "KSLA2022_SEC_0002": ["risk", "diagnosis"],                       # 제5판 주요 변경사항
    "KSLA2022_SEC_0003": ["risk"],                                    # 근거수준 및 권고등급 정의
    # ── Chapter 1. 역학·위험도 ────────────────────────────────
    "KSLA2022_SEC_0004": ["risk"],                                    # 심혈관질환 현황 (1) 사망률
    "KSLA2022_SEC_0005": ["risk"],                                    # 심혈관질환 현황 (2) 위험요인·유병률
    "KSLA2022_SEC_0006": ["risk"],                                    # 위험요인과 위험도 평가 — 개요
    "KSLA2022_SEC_0007": ["risk"],                                    # 위험도 평가 — 표 1-1 기여위험도
    "KSLA2022_SEC_0008": ["risk"],                                    # 위험도 평가 — 표 1-2 비교위험도
    "KSLA2022_SEC_0009": ["screening", "diagnosis"],                  # 혈중 지질 농도 분포 (1)
    "KSLA2022_SEC_0010": ["screening", "diagnosis"],                  # 혈중 지질 농도 분포 (2) 유병률
    # ── Chapter 2. 진단·치료 기준 ─────────────────────────────
    "KSLA2022_SEC_0011": ["diagnosis", "screening"],                  # 진단 방법 및 분류 기준 (1) 선별검사
    "KSLA2022_SEC_0012": ["diagnosis"],                               # 진단 방법 및 분류 기준 (2) 기준표
    "KSLA2022_SEC_0013": ["risk", "medication"],                      # 치료 기준 — LDL 목표치 전체 권고안
    "KSLA2022_SEC_0014": ["risk", "medication"],                      # 치료 기준 — 고중성지방혈증·고LDL
    "KSLA2022_SEC_0015": ["risk"],                                    # 치료 기준 — 서론·주요 위험인자
    "KSLA2022_SEC_0016": ["risk", "medication"],                      # 초고위험군 LDL <55 근거
    "KSLA2022_SEC_0017": ["risk", "medication"],                      # 고위험군 LDL <70 근거
    "KSLA2022_SEC_0018": ["risk", "complication"],                    # 당뇨병 심혈관질환 고위험 근거
    "KSLA2022_SEC_0019": ["risk", "medication"],                      # 위험도별 LDL 치료 기준표 해설
    "KSLA2022_SEC_0020": ["risk", "medication"],                      # 중등도 위험군 LDL 목표
    "KSLA2022_SEC_0021": ["risk", "medication"],                      # 저위험군 LDL 목표
    "KSLA2022_SEC_0022": ["risk", "medication"],                      # 고중성지방혈증 치료지침
    "KSLA2022_SEC_0023": ["risk", "medication"],                      # 결론·가이드라인 비교
    "KSLA2022_SEC_0024": ["monitoring"],                              # 경과 모니터링
    # ── Chapter 3. 생활습관요법 ───────────────────────────────
    "KSLA2022_SEC_0025": ["diet", "lifestyle"],                       # 식사요법 — 고콜레스테롤혈증 에너지·지방
    "KSLA2022_SEC_0026": ["diet", "lifestyle"],                       # 식사요법 — 트랜스지방·콜레스테롤·탄수화물
    "KSLA2022_SEC_0027": ["diet", "lifestyle"],                       # 식사요법 — 고중성지방혈증 에너지·지방
    "KSLA2022_SEC_0028": ["diet", "lifestyle", "alcohol"],            # 식사요법 — 고중성지방혈증 탄수화물·알코올
    "KSLA2022_SEC_0029": ["diet", "lifestyle"],                       # 식사요법 — 저HDL 지방·탄수화물
    "KSLA2022_SEC_0030": ["diet", "lifestyle"],                       # 식사요법 — 식사패턴·가이드
    "KSLA2022_SEC_0031": ["diet"],                                    # 식사요법 — 권장식품·주의식품 표
    "KSLA2022_SEC_0032": ["exercise", "lifestyle"],                   # 운동요법
    "KSLA2022_SEC_0033": ["lifestyle", "smoking", "alcohol"],         # 금연 / 절주
    # ── Chapter 4. 약물치료 ───────────────────────────────────
    "KSLA2022_SEC_0034": ["medication"],                              # 약제의 선택 — LDL·non-HDL·병용요법
    "KSLA2022_SEC_0035": ["medication"],                              # 약제의 선택 — 저HDL·TG 권고안
    "KSLA2022_SEC_0036": ["medication"],                              # 약제의 선택 — 고콜레스테롤혈증 알고리즘
    "KSLA2022_SEC_0037": ["medication"],                              # 약제의 선택 — 고중성지방혈증·스타틴
    "KSLA2022_SEC_0038": ["medication"],                              # 비스타틴 — 피브린산·니코틴산
    "KSLA2022_SEC_0039": ["medication"],                              # 비스타틴 — 오메가-3·에제티미브·PCSK9
    "KSLA2022_SEC_0040": ["medication"],                              # 스타틴 — 서론·역사·기전·종류
    "KSLA2022_SEC_0041": ["medication"],                              # 스타틴 — 용법·용량·부작용
    "KSLA2022_SEC_0042": ["medication", "monitoring"],                # 스타틴 — 금기증·추적관찰
    "KSLA2022_SEC_0043": ["medication"],                              # 에제티미브 — 서론·기전·임상연구
    "KSLA2022_SEC_0044": ["medication"],                              # 에제티미브 — 부작용·금기증
    "KSLA2022_SEC_0045": ["medication"],                              # PCSK9 억제제 — 서론·적응증·기전
    "KSLA2022_SEC_0046": ["medication"],                              # PCSK9 억제제 — 임상연구·부작용
    "KSLA2022_SEC_0047": ["medication"],                              # 피브린산 유도체 — 서론·기전
    "KSLA2022_SEC_0048": ["medication"],                              # 피브린산 유도체 — 임상연구
    "KSLA2022_SEC_0049": ["medication"],                              # 피브린산 유도체 — 부작용·금기증
    "KSLA2022_SEC_0050": ["medication"],                              # 오메가-3 지방산 — 서론·기전
    "KSLA2022_SEC_0051": ["medication"],                              # 오메가-3 지방산 — 임상연구·부작용
    "KSLA2022_SEC_0052": ["medication"],                              # 니코틴산 — 서론·기전
    "KSLA2022_SEC_0053": ["medication"],                              # 니코틴산·담즙산결합수지
    "KSLA2022_SEC_0054": ["medication"],                              # 병용요법 (1) — 스타틴+에제티미브
    "KSLA2022_SEC_0055": ["medication"],                              # 병용요법 (2) — 스타틴+PCSK9
    "KSLA2022_SEC_0056": ["medication"],                              # 병용요법 (3) — 스타틴+피브린산·오메가-3
    # ── Chapter 5. 특수 상황 ──────────────────────────────────
    "KSLA2022_SEC_0057": ["complication", "medication"],              # 관상동맥질환 — 스타틴 근거
    "KSLA2022_SEC_0058": ["complication", "medication"],              # 관상동맥질환 — 에제티미브·PCSK9
    "KSLA2022_SEC_0059": ["complication", "medication"],              # 뇌졸중 — 권고안
    "KSLA2022_SEC_0060": ["complication", "medication"],              # 뇌졸중 — 죽상경화증 치료
    "KSLA2022_SEC_0061": ["complication", "risk", "medication"],      # 뇌졸중 — 고위험 LDL 목표치
    "KSLA2022_SEC_0062": ["complication", "medication"],              # 만성콩팥병 — 권고안
    "KSLA2022_SEC_0063": ["complication", "medication"],              # 만성콩팥병 — 임상연구
    "KSLA2022_SEC_0064": ["complication", "medication"],              # 만성콩팥병과 이상지질혈증
    "KSLA2022_SEC_0065": ["complication", "diagnosis", "medication"], # 당뇨병 — 권고안
    "KSLA2022_SEC_0066": ["complication", "monitoring"],              # 당뇨병 — 추적관리
    "KSLA2022_SEC_0067": ["complication", "medication"],              # 당뇨병 — 치료목표
    "KSLA2022_SEC_0068": ["complication", "medication", "lifestyle"], # 당뇨병 — 치료 (생활습관·스타틴)
    "KSLA2022_SEC_0069": ["complication", "medication"],              # 당뇨병 — 스타틴 병용요법
    "KSLA2022_SEC_0070": ["risk", "medication"],                      # 노인의 이상지질혈증
    "KSLA2022_SEC_0071": ["pediatric", "screening"],                  # 소아청소년 — 권고안·역학
    "KSLA2022_SEC_0072": ["pediatric", "diagnosis", "screening"],     # 소아청소년 — 진단
    "KSLA2022_SEC_0073": ["pediatric", "diet", "lifestyle"],          # 소아청소년 — 식사요법·생활습관
    "KSLA2022_SEC_0074": ["pediatric", "medication"],                 # 소아청소년 — 약물치료·FH
    "KSLA2022_SEC_0075": ["diagnosis"],                               # 가족성 고콜레스테롤혈증 (FH) — 진단기준
    "KSLA2022_SEC_0076": ["medication"],                              # 가족성 고콜레스테롤혈증 (FH) — 치료
    "KSLA2022_SEC_0077": ["complication", "risk"],                    # 임신 중 이상지질혈증 — 권고안·지질대사
    "KSLA2022_SEC_0078": ["complication"],                            # 임신 중 — 지질의 태반통과
    "KSLA2022_SEC_0079": ["complication"],                            # 임신 중 — 합병증
    "KSLA2022_SEC_0080": ["complication", "medication", "lifestyle"], # 임신 중 — 치료
    # ── figures (기존 유지) ───────────────────────────────────
    "DYS_FIG_001": ["diagnosis"],
    "DYS_FIG_002": ["medication", "risk"],
    "DYS_FIG_003": ["medication", "risk"],
    "DYS_FIG_004": ["risk"],
    "DYS_FIG_005": ["diet"],
    "DYS_FIG_005A": ["diagnosis", "medication"],
    "DYS_FIG_005B": ["diagnosis", "medication"],
    "DYS_FIG_007": ["diagnosis"],
    "DYS_FIG_012": ["diagnosis"],
}

# ══════════════════════════════════════════════════════════════
# GUIDE — 서비스 이용 가이드 (source_id: GUIDE)
# ══════════════════════════════════════════════════════════════
_GUIDE: dict[str, list[str]] = {
    "GUIDE_SEC_001": ["service"],
    "GUIDE_SEC_002": ["service"],
    "GUIDE_SEC_003": ["service"],
    "GUIDE_SEC_004": ["service"],
    "GUIDE_SEC_005": ["service", "challenge"],
    "GUIDE_SEC_006": ["service"],
    "GUIDE_SEC_007": ["service"],
    "GUIDE_SEC_008": ["service"],
    "GUIDE_SEC_008A": ["service"],
    "GUIDE_SEC_008B": ["service"],
    "GUIDE_SEC_008C": ["service"],
    "GUIDE_SEC_008D": ["service"],
    "GUIDE_SEC_009": ["service"],
    "GUIDE_SEC_010": ["service"],
    "GUIDE_SEC_011": ["service"],
    "GUIDE_SEC_012": ["service"],
    "GUIDE_SEC_013": ["service"],
    "GUIDE_SEC_014": ["service"],
    "GUIDE_SEC_015": ["service"],
    "GUIDE_SEC_016": ["service"],
    "GUIDE_SEC_017": ["service"],
    "GUIDE_SEC_018": ["service"],
    "GUIDE_SEC_019": ["service", "challenge"],
    "GUIDE_SEC_020": ["service", "challenge"],
    "GUIDE_SEC_020A": ["service"],
    "GUIDE_SEC_021": ["service"],
    "GUIDE_SEC_022": ["service"],
    "GUIDE_SEC_023": ["service"],
    "GUIDE_SEC_024": ["service", "challenge"],
    "GUIDE_SEC_025": ["service"],
    "GUIDE_SEC_026": ["service"],
    "GUIDE_SEC_027": ["service"],
}

# ══════════════════════════════════════════════════════════════
# CHALLENGE_CATALOG — 챌린지 카탈로그 (source_id: CHALLENGE_CATALOG)
# ══════════════════════════════════════════════════════════════
_CHALLENGE_CATALOG: dict[str, list[str]] = {
    "CHALL_SEC_0001": ["challenge", "service"],
    "CHALL_SEC_0002": ["challenge", "service"],
    "CHALL_SEC_0003": ["challenge", "service"],
    "CHALL_SEC_0004": ["challenge", "exercise"],
    "CHALL_SEC_0005": ["challenge", "exercise"],
    "CHALL_SEC_0006": ["challenge", "exercise"],
    "CHALL_SEC_0007": ["challenge", "exercise"],
    "CHALL_SEC_0008": ["challenge", "exercise"],
    "CHALL_SEC_0009": ["challenge", "exercise"],
    "CHALL_SEC_0010": ["challenge", "diet"],
    "CHALL_SEC_0011": ["challenge", "lifestyle"],
    "CHALL_SEC_0012": ["challenge", "diet"],
    "CHALL_SEC_0013": ["challenge", "weight"],
    "CHALL_SEC_0014": ["challenge", "smoking"],
    "CHALL_SEC_0015": ["challenge", "alcohol"],
    "CHALL_SEC_0016": ["challenge", "lifestyle"],
    "CHALL_SEC_0017": ["challenge", "lifestyle", "complication"],
    "CHALL_SEC_0018": ["challenge", "service"],
    "CHALL_SEC_0019": ["challenge", "service"],
    "CHALL_SEC_0020": ["challenge", "service"],
    "CHALL_SEC_0021": ["challenge", "lifestyle", "risk"],
    "CHALL_SEC_0022": ["challenge", "service"],
}

# ══════════════════════════════════════════════════════════════
# 전체 통합 매핑
# ══════════════════════════════════════════════════════════════
TOPIC_MAPPING: dict[str, list[str]] = {
    **_KDA2025,
    **_KSH2026,
    **_KSLA2022,
    **_GUIDE,
    **_CHALLENGE_CATALOG,
}


def _get_topics(section_id: str) -> list[str]:
    """섹션 ID로 topic 목록 조회. 매핑 없으면 빈 리스트."""
    return TOPIC_MAPPING.get(section_id, [])
