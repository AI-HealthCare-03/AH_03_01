import type { Metadata } from "next";
import "./globals.css";
import Providers from "@/components/layout/Providers";

export const metadata: Metadata = {
  title: {
    default: "헬씨루틴 — 매일 5분으로 만성질환을 관리해요",
    template: "%s | 헬씨루틴",
  },
  description:
    "혈압·혈당·생활습관 챌린지로 만성질환을 스스로 관리하는 서비스입니다. 본 서비스는 의학적 진단을 대체하지 않습니다.",
  keywords: ["만성질환", "혈압", "혈당", "건강관리", "챌린지"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
