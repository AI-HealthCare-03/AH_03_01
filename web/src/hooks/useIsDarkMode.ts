"use client";

import { useEffect, useState } from "react";

/* html.dark 클래스 토글을 감지 — recharts 등 인라인 색상(hex) 컴포넌트는
   CSS 다크모드 오버라이드가 적용되지 않아 JS에서 직접 분기해야 함. */
export function useIsDarkMode(): boolean {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const root = document.documentElement;
    setIsDark(root.classList.contains("dark"));

    const observer = new MutationObserver(() => {
      setIsDark(root.classList.contains("dark"));
    });
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });

    return () => observer.disconnect();
  }, []);

  return isDark;
}
