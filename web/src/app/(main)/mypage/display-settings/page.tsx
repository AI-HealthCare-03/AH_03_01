"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

/* ─────────────────────────────────────────────────────
   화면 설정 페이지
   - 화면 모드 (라이트 / 다크 / 시스템 설정 따름)
   - 폰트 크기 (작게 14px / 보통 16px / 크게 18px / 매우 크게 20px)
   localStorage 에 저장, 새로고침 후에도 유지.
───────────────────────────────────────────────────── */

type ThemeMode = "light" | "dark" | "system";
type FontSize = "14" | "16" | "18" | "20";

const THEME_KEY = "theme-mode";
const FONT_KEY = "font-size";

const THEME_OPTIONS: { value: ThemeMode; label: string; preview: string }[] = [
  { value: "light",  label: "라이트 모드",    preview: "bg-white border-2 border-gray-200" },
  { value: "dark",   label: "다크 모드",      preview: "bg-[#0d1117]" },
  { value: "system", label: "시스템 설정 따름", preview: "bg-gradient-to-br from-white to-[#0d1117]" },
];

const FONT_OPTIONS: { value: FontSize; label: string }[] = [
  { value: "14", label: "작게 (14px)" },
  { value: "16", label: "보통 (16px)" },
  { value: "18", label: "크게 (18px)" },
  { value: "20", label: "매우 크게 (20px)" },
];

function applyTheme(mode: ThemeMode) {
  const html = document.documentElement;
  let isDark = false;
  if (mode === "dark") isDark = true;
  else if (mode === "system") isDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

  if (isDark) {
    html.style.setProperty("--ui-page-bg", "#1a1a1a");
    html.classList.add("dark");
  } else {
    html.style.removeProperty("--ui-page-bg");
    html.classList.remove("dark");
  }
}

function applyFontSize(size: FontSize) {
  document.documentElement.style.fontSize = `${size}px`;
}

export default function DisplaySettingsPage() {
  const [theme, setTheme] = useState<ThemeMode>("light");
  const [fontSize, setFontSize] = useState<FontSize>("16");

  /* 초기 로드 */
  useEffect(() => {
    const savedTheme = (localStorage.getItem(THEME_KEY) as ThemeMode) ?? "light";
    const savedFont  = (localStorage.getItem(FONT_KEY)  as FontSize)  ?? "16";
    setTheme(savedTheme);
    setFontSize(savedFont);
    applyTheme(savedTheme);
    applyFontSize(savedFont);
  }, []);

  const handleThemeChange = (mode: ThemeMode) => {
    setTheme(mode);
    localStorage.setItem(THEME_KEY, mode);
    applyTheme(mode);
  };

  const handleFontChange = (size: FontSize) => {
    setFontSize(size);
    localStorage.setItem(FONT_KEY, size);
    applyFontSize(size);
  };

  return (
    <div className="max-w-2xl mx-auto px-5 py-6 space-y-5">
      {/* 헤더 */}
      <div className="flex items-center gap-3">
        <Link href="/mypage" className="text-text-tertiary hover:text-text-primary">
          ←
        </Link>
        <h1 className="text-xl font-black text-text-primary">화면 설정</h1>
      </div>

      {/* 화면 모드 */}
      <section className="bg-white border border-border rounded-[16px] p-5 space-y-4">
        <p className="text-sm font-bold text-text-primary">화면 모드</p>
        <div className="grid grid-cols-3 gap-3">
          {THEME_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => handleThemeChange(opt.value)}
              className={[
                "flex flex-col items-center gap-2 p-3 rounded-[12px] border-2 transition-colors",
                theme === opt.value
                  ? "border-brand-black"
                  : "border-border hover:border-text-tertiary",
              ].join(" ")}
            >
              <div className={`w-full aspect-[4/3] rounded-[8px] ${opt.preview}`} />
              <span className="text-xs text-text-primary font-medium text-center leading-tight">
                {opt.label}
                {theme === opt.value && " ✓"}
              </span>
            </button>
          ))}
        </div>
      </section>

      {/* 폰트 크기 */}
      <section className="bg-white border border-border rounded-[16px] p-5 space-y-4">
        <p className="text-sm font-bold text-text-primary">폰트 크기</p>
        <div className="flex items-center justify-between gap-2">
          {FONT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => handleFontChange(opt.value)}
              className={[
                "flex-1 py-2 text-center rounded-[10px] border transition-colors text-xs",
                fontSize === opt.value
                  ? "border-brand-black bg-brand-black text-white font-semibold"
                  : "border-border text-text-secondary hover:border-text-primary",
              ].join(" ")}
            >
              {opt.label}
            </button>
          ))}
        </div>
        {/* 진행 바 */}
        <div className="relative h-1.5 bg-border rounded-full">
          <div
            className="absolute top-0 left-0 h-full bg-brand-black rounded-full transition-all"
            style={{
              width: `${(FONT_OPTIONS.findIndex((o) => o.value === fontSize) / (FONT_OPTIONS.length - 1)) * 100}%`,
            }}
          />
        </div>
        <p className="text-xs text-text-tertiary">
          데이터 시각화 차트의 라벨 크기도 함께 조정됩니다.
        </p>
      </section>
    </div>
  );
}
