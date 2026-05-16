import type { ReactNode } from "react";

/* (auth) 그룹 레이아웃 — GNB 없이 순수 auth 화면만 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
