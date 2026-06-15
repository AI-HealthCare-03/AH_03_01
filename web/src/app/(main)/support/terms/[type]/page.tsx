"use client";

import Link from "next/link";
import { useParams, notFound } from "next/navigation";

/* =========================================
   ※ 서비스/포트폴리오용 초안이며 법적 효력을 보장하지 않습니다.
   ========================================= */

const TERMS_NAV = [
  { type: "service",   label: "이용약관" },
  { type: "privacy",   label: "개인정보 처리방침" },
  { type: "location",  label: "위치기반 서비스" },
  { type: "opensource", label: "오픈소스 라이선스" },
] as const;

type TermsType = (typeof TERMS_NAV)[number]["type"];

interface TermsSection {
  heading: string;
  paragraphs: string[];
}

interface TermsData {
  title: string;
  effectiveDate: string;
  intro: string;
  sections: TermsSection[];
}

/* ─────────────────────────────────────────────────────────
   이용약관  (app/terms/page.tsx 내용과 동일)
───────────────────────────────────────────────────────── */
const SERVICE_SECTIONS: TermsSection[] = [
  {
    heading: "제1조 (목적)",
    paragraphs: [
      "본 약관은 케어로그(이하 '회사')가 제공하는 만성질환(고혈압·당뇨) 생활습관 관리 및 챌린지 서비스(이하 '서비스')의 이용과 관련하여 회사와 회원 간의 권리, 의무 및 책임사항을 규정함을 목적으로 합니다.",
    ],
  },
  {
    heading: "제2조 (정의)",
    paragraphs: [
      "1. '서비스'란 회원이 건강 정보를 기록하고, AI 기반 위험도 참고 지표·생활습관 추천, 챌린지, 펫 키우기 등 부가 기능을 이용할 수 있도록 회사가 제공하는 일체의 서비스를 말합니다.",
      "2. '회원'이란 본 약관에 동의하고 회원가입을 완료하여 서비스를 이용하는 자를 말합니다.",
      "3. '계정'이란 회원의 식별과 서비스 이용을 위해 회원이 설정하고 회사가 승인한 이메일 및 비밀번호를 말합니다.",
    ],
  },
  {
    heading: "제3조 (약관의 효력 및 변경)",
    paragraphs: [
      "1. 본 약관은 서비스 화면에 게시하거나 기타의 방법으로 회원에게 공지함으로써 효력이 발생합니다.",
      "2. 회사는 관련 법령을 위배하지 않는 범위에서 약관을 변경할 수 있으며, 변경 시 적용일자 및 변경사유를 명시하여 시행일 7일 이전부터 공지합니다. 회원에게 불리한 변경의 경우 30일 이전에 공지합니다.",
    ],
  },
  {
    heading: "제4조 (이용계약의 성립)",
    paragraphs: [
      "1. 이용계약은 회원이 되고자 하는 자가 약관에 동의하고 가입 신청을 한 후, 회사가 이를 승낙함으로써 성립합니다.",
      "2. 회사는 가입 신청자가 타인의 정보를 도용하거나 허위 정보를 기재한 경우, 만 14세 미만인 경우 등에는 승낙을 거부하거나 사후에 이용계약을 해지할 수 있습니다.",
    ],
  },
  {
    heading: "제5조 (회원정보의 관리)",
    paragraphs: [
      "1. 회원은 계정 정보를 직접 관리할 책임이 있으며, 이를 제3자에게 양도하거나 공유할 수 없습니다.",
      "2. 회원은 계정이 도용되거나 제3자가 무단으로 사용하고 있음을 인지한 경우 즉시 회사에 통지하고 안내에 따라야 합니다.",
    ],
  },
  {
    heading: "제6조 (서비스의 제공 및 변경)",
    paragraphs: [
      "1. 회사는 연중무휴, 1일 24시간 서비스를 제공함을 원칙으로 합니다. 다만 시스템 점검·교체, 고장, 통신 두절 등의 사유가 있는 경우 서비스 제공을 일시 중단할 수 있습니다.",
      "2. 회사는 서비스의 내용을 변경할 수 있으며, 변경 시 그 내용을 사전에 공지합니다.",
    ],
  },
  {
    heading: "제7조 (회원의 의무)",
    paragraphs: [
      "회원은 다음 행위를 하여서는 안 됩니다.",
      "1. 타인의 정보 도용 또는 허위 정보 등록\n2. 서비스의 정상적인 운영을 방해하는 행위\n3. 회사 또는 제3자의 지식재산권을 침해하는 행위\n4. 기타 관련 법령 또는 본 약관에 위배되는 행위",
    ],
  },
  {
    heading: "제8조 (의료적 책임의 한계)",
    paragraphs: [
      "1. 본 서비스가 제공하는 위험도 참고 지표, 생활습관 추천, 챗봇 응답 등은 일반적인 건강 정보 제공 및 생활습관 개선 지원을 목적으로 하며, 의학적 진단·치료·처방을 대체하지 않습니다.",
      "2. 회원은 건강상의 결정을 내리기 전 반드시 의사 등 전문 의료인과 상담하여야 하며, 본 서비스의 정보에만 의존하여 발생한 결과에 대해 회사는 책임을 지지 않습니다.",
      "3. 응급 상황이라고 판단되는 경우 즉시 119 또는 의료기관에 연락하시기 바랍니다.",
    ],
  },
  {
    heading: "제9조 (회원 탈퇴 및 이용 제한)",
    paragraphs: [
      "1. 회원은 언제든지 서비스 내 탈퇴 기능을 통해 이용계약을 해지할 수 있습니다.",
      "2. 회사는 회원이 본 약관을 위반하거나 서비스의 정상적인 운영을 방해한 경우, 사전 통지 후 서비스 이용을 제한하거나 이용계약을 해지할 수 있습니다.",
    ],
  },
  {
    heading: "제10조 (면책조항)",
    paragraphs: [
      "1. 회사는 천재지변, 회원의 귀책사유, 통신 서비스 장애 등 회사의 합리적 통제를 벗어난 사유로 서비스를 제공할 수 없는 경우 책임이 면제됩니다.",
      "2. 회사는 회원이 서비스에 게재한 정보·자료의 신뢰도·정확성에 대하여 책임을 지지 않습니다.",
    ],
  },
  {
    heading: "제11조 (준거법 및 관할)",
    paragraphs: [
      "본 약관은 대한민국 법령에 따라 해석되며, 서비스 이용과 관련하여 분쟁이 발생한 경우 민사소송법상의 관할 법원을 제1심 관할 법원으로 합니다.",
    ],
  },
  {
    heading: "부칙",
    paragraphs: ["본 약관은 2026년 6월 5일부터 시행합니다."],
  },
];

/* ─────────────────────────────────────────────────────────
   개인정보 처리방침  (app/privacy/page.tsx 내용과 동일)
───────────────────────────────────────────────────────── */
const PRIVACY_SECTIONS: TermsSection[] = [
  {
    heading: "1. 수집하는 개인정보 항목",
    paragraphs: [
      "회사는 회원가입 및 서비스 제공을 위해 다음의 개인정보를 수집합니다.",
      "[필수 항목]\n- 이메일(계정 ID), 비밀번호, 이름, 닉네임, 휴대폰 번호, 생년월일, 성별",
      "[민감정보 — 건강정보]\n- 혈압·혈당 등 건강 기록, 복용 약물 정보, 만성질환 관련 입력 정보\n- 건강정보는 개인정보 보호법 제23조에 따른 민감정보로, 회원의 별도 동의를 받아 처리하며 서비스 제공 목적 외로 이용하지 않습니다.",
      "[자동 수집 항목]\n- 서비스 이용 기록, 접속 로그, 기기 정보(브라우저·OS), IP 주소",
    ],
  },
  {
    heading: "2. 개인정보의 수집 및 이용 목적",
    paragraphs: [
      "1. 회원 식별 및 본인 확인, 회원 관리, 부정 이용 방지",
      "2. 건강 기록 관리, AI 기반 위험도 참고 지표 및 생활습관 추천 제공",
      "3. 챌린지·펫 키우기 등 서비스 기능 제공 및 보상 지급",
      "4. 공지사항 전달, 문의 응대 등 고객 지원",
    ],
  },
  {
    heading: "3. 개인정보의 보유 및 이용 기간",
    paragraphs: [
      "1. 회원 탈퇴 시 회사는 개인정보를 즉시 파기하지 않고, 탈퇴 처리(soft delete) 후 30일간 보관한 뒤 파기합니다. 이는 탈퇴 철회 요청 대응, 부정 이용 방지 및 분쟁 처리를 위한 것이며, 보관 기간 동안 회원의 서비스 이용은 제한됩니다.",
      "2. 보관 기간 30일이 경과하면 회원의 개인정보를 복구 불가능한 방법으로 지체 없이 파기합니다.",
      "3. 다만 관련 법령에 따라 보존이 필요한 경우 해당 기간 동안 보관합니다.\n- 계약 또는 청약철회 등에 관한 기록: 5년 (전자상거래법)\n- 소비자 불만 또는 분쟁 처리에 관한 기록: 3년 (전자상거래법)\n- 접속에 관한 기록: 3개월 (통신비밀보호법)",
    ],
  },
  {
    heading: "4. 개인정보의 제3자 제공",
    paragraphs: [
      "회사는 회원의 개인정보를 본 방침에서 고지한 범위를 넘어 제3자에게 제공하지 않습니다. 다만 법령에 근거하거나 회원의 별도 동의가 있는 경우는 예외로 합니다.",
    ],
  },
  {
    heading: "5. 개인정보 처리의 위탁",
    paragraphs: [
      "회사는 원활한 서비스 제공을 위해 다음과 같이 개인정보 처리 업무를 위탁할 수 있으며, 위탁 시 수탁자가 개인정보를 안전하게 처리하도록 관리·감독합니다.",
      "- 이메일 발송(본인 인증 메일 등): 이메일 발송 서비스 제공업체\n- 서버 운영 및 데이터 보관: 클라우드 인프라 제공업체",
    ],
  },
  {
    heading: "6. 정보주체의 권리와 행사 방법",
    paragraphs: [
      "1. 회원은 언제든지 자신의 개인정보를 조회·수정하거나 처리 정지·삭제(탈퇴)를 요청할 수 있습니다.",
      "2. 권리 행사는 서비스 내 설정 메뉴 또는 개인정보 보호책임자에게 연락하여 할 수 있으며, 회사는 지체 없이 조치합니다.",
    ],
  },
  {
    heading: "7. 개인정보의 파기 절차 및 방법",
    paragraphs: [
      "1. 보유 기간이 경과하거나 처리 목적이 달성된 개인정보는 지체 없이 파기합니다.",
      "2. 전자적 파일은 복구가 불가능한 방법으로 영구 삭제하며, 출력물은 분쇄하거나 소각합니다.",
    ],
  },
  {
    heading: "8. 개인정보의 안전성 확보 조치",
    paragraphs: [
      "회사는 개인정보 보호를 위해 다음의 조치를 취합니다.",
      "- 비밀번호의 일방향 암호화 저장\n- 개인정보 접근 권한의 최소화 및 접근 통제\n- 전송 구간 암호화(HTTPS) 적용\n- 접속 기록의 보관 및 위변조 방지",
    ],
  },
  {
    heading: "9. 개인정보 보호책임자",
    paragraphs: [
      "회사는 개인정보 처리에 관한 업무를 총괄하는 보호책임자를 두고 있습니다.",
      "- 개인정보 보호책임자: 케어로그 운영팀\n- 문의: privacy@carelog.example",
      "회원은 개인정보 관련 문의·불만·피해구제를 위 연락처로 문의할 수 있습니다.",
    ],
  },
  {
    heading: "부칙",
    paragraphs: ["본 방침은 2026년 6월 5일부터 시행합니다."],
  },
];

/* ─────────────────────────────────────────────────────────
   위치기반서비스 이용약관  (REQ-CS-011)
───────────────────────────────────────────────────────── */
const LOCATION_SECTIONS: TermsSection[] = [
  {
    heading: "제1조 (목적)",
    paragraphs: [
      "본 약관은 케어로그(이하 '회사')가 위치정보의 보호 및 이용 등에 관한 법률에 따라 위치기반서비스를 제공함에 있어 회사와 회원의 권리·의무 및 책임사항을 규정함을 목적으로 합니다.",
    ],
  },
  {
    heading: "제2조 (위치기반서비스의 내용)",
    paragraphs: [
      "회사는 회원의 위치정보를 기반으로 다음의 서비스를 제공합니다.",
      "1. 현재 위치 또는 설정 위치 기반 인근 의료기관·약국 정보 제공\n2. 위치 기반 건강 관련 생활습관 추천\n3. 기타 위치정보를 활용한 맞춤형 서비스",
    ],
  },
  {
    heading: "제3조 (위치정보의 수집·이용·제공)",
    paragraphs: [
      "1. 회사는 위치기반서비스 제공을 위해 회원의 사전 동의를 받아 위치정보를 수집·이용합니다.",
      "2. 수집된 위치정보는 서비스 제공 외의 목적으로 이용되거나 제3자에게 제공되지 않습니다. 다만 법령에 근거하거나 회원의 별도 동의가 있는 경우는 예외로 합니다.",
      "3. 위치정보는 서비스 제공 즉시 파기하며 별도 보관하지 않습니다.",
    ],
  },
  {
    heading: "제4조 (위치정보 이용·제공 사실 확인자료의 보관)",
    paragraphs: [
      "회사는 위치정보 보호법 제16조 제2항에 따라 위치정보 이용·제공 사실 확인자료를 자동으로 기록·보존하며, 해당 자료는 6개월간 보관합니다.",
    ],
  },
  {
    heading: "제5조 (이용자의 권리)",
    paragraphs: [
      "1. 회원은 위치정보 수집·이용·제공에 대한 동의를 언제든지 전부 또는 일부 철회할 수 있습니다.",
      "2. 회원은 위치정보 수집 일시 중지를 요청할 수 있으며, 이 경우 위치기반서비스 이용이 제한될 수 있습니다.",
      "3. 위치정보 관련 문의 및 권리 행사는 서비스 내 고객센터를 통해 접수할 수 있습니다.",
    ],
  },
  {
    heading: "제6조 (위치정보관리책임자)",
    paragraphs: [
      "회사는 위치정보를 적절히 관리·보호하기 위해 위치정보관리책임자를 지정합니다.",
      "- 위치정보관리책임자: 케어로그 운영팀\n- 문의: privacy@carelog.example",
    ],
  },
  {
    heading: "부칙",
    paragraphs: ["본 약관은 2026년 6월 5일부터 시행합니다."],
  },
];

/* ─────────────────────────────────────────────────────────
   오픈소스 라이선스  (NFR-011-004 — 실제 사용 패키지 기준)
───────────────────────────────────────────────────────── */
const OPENSOURCE_SECTIONS: TermsSection[] = [
  {
    heading: "개요",
    paragraphs: [
      "본 서비스는 아래 오픈소스 소프트웨어를 활용하여 개발되었습니다. 각 라이브러리의 라이선스 조건을 준수하며 사용하고 있습니다.",
    ],
  },
  {
    heading: "프론트엔드",
    paragraphs: [
      "Next.js — MIT License\nCopyright (c) 2024 Vercel, Inc.",
      "React — MIT License\nCopyright (c) Meta Platforms, Inc. and affiliates.",
      "TanStack Query (React Query) — MIT License\nCopyright (c) 2021 Tanner Linsley.",
      "Tailwind CSS — MIT License\nCopyright (c) 2020 Tailwind Labs Inc.",
      "TypeScript — Apache License 2.0\nCopyright (c) Microsoft Corporation.",
      "Axios — MIT License\nCopyright (c) 2014-present Matt Zabriskie & Collaborators.",
    ],
  },
  {
    heading: "백엔드",
    paragraphs: [
      "FastAPI — MIT License\nCopyright (c) 2018 Sebastian Ramirez.",
      "Tortoise ORM — Apache License 2.0\nCopyright (c) 2018 Nicklas Damgren & contributors.",
      "Pydantic — MIT License\nCopyright (c) 2017 Samuel Colvin.",
      "PyJWT — MIT License\nCopyright (c) 2015-2022 Jose Padilla.",
      "asyncpg — Apache License 2.0\nCopyright (c) 2016-present the asyncpg authors.",
      "Redis (redis-py) — MIT License\nCopyright (c) 2012 Andy McCurdy.",
    ],
  },
  {
    heading: "AI / ML",
    paragraphs: [
      "PyTorch — BSD 3-Clause License\nCopyright (c) 2016 Facebook, Inc. All rights reserved.",
      "scikit-learn — BSD 3-Clause License\nCopyright (c) 2007-2024 The scikit-learn developers.",
      "sentence-transformers — Apache License 2.0\nCopyright (c) 2019 Nils Reimers.",
      "LangGraph / LangChain — MIT License\nCopyright (c) 2023 LangChain, Inc.",
      "NumPy — BSD 3-Clause License\nCopyright (c) 2005-2024 NumPy Developers.",
    ],
  },
  {
    heading: "라이선스 전문",
    paragraphs: [
      "각 라이선스의 전문은 해당 프로젝트의 공식 저장소에서 확인할 수 있습니다. 라이선스 관련 문의는 고객센터를 통해 접수해 주세요.",
    ],
  },
];

/* ─────────────────────────────────────────────────────────
   통합 데이터
───────────────────────────────────────────────────────── */
const TERMS_CONTENT: Record<TermsType, TermsData> = {
  service: {
    title: "이용약관",
    effectiveDate: "2026년 6월 5일",
    intro: "본 약관은 케어로그 서비스 이용에 관한 기본 사항을 정합니다. 본 문서는 서비스 이해를 돕기 위한 초안으로, 법적 효력을 보장하지 않습니다.",
    sections: SERVICE_SECTIONS,
  },
  privacy: {
    title: "개인정보 처리방침",
    effectiveDate: "2026년 6월 5일",
    intro: "케어로그(이하 '회사')는 회원의 개인정보를 중요하게 생각하며, 개인정보 보호법 등 관련 법령을 준수합니다. 본 문서는 서비스 이해를 돕기 위한 초안으로, 법적 효력을 보장하지 않습니다.",
    sections: PRIVACY_SECTIONS,
  },
  location: {
    title: "위치기반서비스 이용약관",
    effectiveDate: "2026년 6월 5일",
    intro: "본 약관은 위치정보의 보호 및 이용 등에 관한 법률에 따라 케어로그가 제공하는 위치기반서비스의 이용 조건을 정합니다.",
    sections: LOCATION_SECTIONS,
  },
  opensource: {
    title: "오픈소스 라이선스",
    effectiveDate: "2026년 6월 5일",
    intro: "본 서비스는 다양한 오픈소스 소프트웨어를 활용하여 개발되었습니다. 각 라이브러리의 라이선스 조건을 준수하며 사용하고 있습니다.",
    sections: OPENSOURCE_SECTIONS,
  },
};

export default function TermsPage() {
  const { type } = useParams<{ type: string }>();

  if (!Object.keys(TERMS_CONTENT).includes(type)) {
    notFound();
  }

  const current = TERMS_CONTENT[type as TermsType];

  return (
    <div className="space-y-5">
      {/* 탭 네비게이션 */}
      <nav className="flex gap-1 flex-wrap">
        {TERMS_NAV.map((item) => (
          <Link
            key={item.type}
            href={`/support/terms/${item.type}`}
            className={[
              "px-3 py-1.5 rounded-full text-sm transition-colors",
              type === item.type
                ? "bg-brand-black text-white font-semibold"
                : "bg-surface text-text-secondary hover:text-text-primary",
            ].join(" ")}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      {/* 본문 */}
      <article className="bg-white border border-border rounded-[16px] p-5 space-y-5">
        <div className="pb-4 border-b border-border">
          <h1 className="text-lg font-black text-text-primary">{current.title}</h1>
          <p className="text-xs text-text-tertiary mt-1">시행일: {current.effectiveDate}</p>
          {current.intro && (
            <p className="text-sm text-text-secondary mt-2 leading-relaxed">
              {current.intro}
            </p>
          )}
        </div>

        <div className="space-y-5">
          {current.sections.map((section) => (
            <section key={section.heading}>
              <h2 className="text-sm font-bold text-text-primary mb-1.5">
                {section.heading}
              </h2>
              {section.paragraphs.map((p, i) => (
                <p
                  key={i}
                  className="text-sm text-text-secondary leading-relaxed whitespace-pre-line mb-1.5"
                >
                  {p}
                </p>
              ))}
            </section>
          ))}
        </div>
      </article>
    </div>
  );
}
