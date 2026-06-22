import Link from "next/link";
import { ROUTES } from "@/constants";

export interface LegalSection {
  heading: string;
  paragraphs: string[];
}

interface LegalDocumentProps {
  title: string;
  effectiveDate: string;
  intro?: string;
  sections: LegalSection[];
}

/* 이용약관 / 개인정보처리방침 등 정적 법적 문서 공용 레이아웃 */
export default function LegalDocument({
  title,
  effectiveDate,
  intro,
  sections,
}: LegalDocumentProps) {
  return (
    <main className="mx-auto max-w-2xl px-5 py-10">
      <Link href={ROUTES.SIGNUP} className="text-sm text-text-secondary underline">
        ← 가입으로 돌아가기
      </Link>
      <h1 className="mt-4 text-2xl font-bold text-text-primary">{title}</h1>
      <p className="mt-1 text-xs text-text-secondary">시행일: {effectiveDate}</p>
      {intro && (
        <p className="mt-4 text-sm text-text-secondary leading-relaxed whitespace-pre-line">
          {intro}
        </p>
      )}
      <div className="mt-6 space-y-6">
        {sections.map((section, i) => (
          <section key={i}>
            <h2 className="mb-2 text-base font-semibold text-text-primary">{section.heading}</h2>
            {section.paragraphs.map((p, j) => (
              <p
                key={j}
                className="mb-1.5 text-sm leading-relaxed text-text-secondary whitespace-pre-line"
              >
                {p}
              </p>
            ))}
          </section>
        ))}
      </div>
    </main>
  );
}
