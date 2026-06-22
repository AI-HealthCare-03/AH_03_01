import type { Metadata } from "next";
import "./globals.css";
import Providers from "@/components/layout/Providers";

export const metadata: Metadata = {
  title: {
    default: "케어로그 — 매일의 케어, 건강의 기록",
    template: "%s | 케어로그",
  },
  description:
    "혈압·혈당·생활습관 챌린지로 만성질환을 스스로 관리하는 서비스입니다. 본 서비스는 의학적 진단을 대체하지 않습니다.",
  keywords: ["만성질환", "혈압", "혈당", "건강관리", "챌린지"],
  icons: {
    icon: [
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon.ico", sizes: "any" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  manifest: "/site.webmanifest",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var theme = localStorage.getItem('theme-mode') || 'light';
                  var font  = localStorage.getItem('font-size')  || '16';
                  var isDark = false;
                  if (theme === 'dark') isDark = true;
                  else if (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches) isDark = true;
                  if (isDark) {
                    document.documentElement.style.setProperty('--ui-page-bg', '#1a1a1a');
                    document.documentElement.classList.add('dark');
                  }
                  document.documentElement.style.fontSize = font + 'px';
                } catch(e) {}
              })();
            `,
          }}
        />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
