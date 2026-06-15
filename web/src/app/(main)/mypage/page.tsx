"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useMe } from "@/hooks/queries/useMe";
import { useMyPet } from "@/hooks/queries/useMyPet";
import { usePointBalance } from "@/hooks/queries/usePointBalance";
import { useWeeklyXp } from "@/hooks/queries/useWeeklyXp";
import { useQuery } from "@tanstack/react-query";
import { fetchHealthProfileDetail } from "@/lib/api/health";
import { resolveMediaUrl } from "@/lib/api/media";
import { useAuth } from "@/hooks/useAuth";
import MedicationManager, { MEDICATION_STORAGE_KEY, type Medication } from "@/components/health/MedicationManager";

/* =========================================
   마이페이지
   - 프로필 카드 (사진/닉네임/이메일/도메인 링크)
   - 읽기 전용 정보
   - 건강 프로필 요약
   - 포인트/펫/주간 EXP
   - 도메인 링크 (출석/리더보드/탈퇴)
   - 로그아웃
   ========================================= */

function genderLabel(g?: "MALE" | "FEMALE") {
  if (g === "MALE") return "남성";
  if (g === "FEMALE") return "여성";
  return "—";
}

function calcAge(birth?: string): number | null {
  if (!birth) return null;
  const d = new Date(birth);
  if (Number.isNaN(d.getTime())) return null;
  const now = new Date();
  let age = now.getFullYear() - d.getFullYear();
  const m = now.getMonth() - d.getMonth();
  if (m < 0 || (m === 0 && now.getDate() < d.getDate())) age--;
  return age;
}

function calcBmi(h?: number, w?: number): string {
  if (!h || !w) return "—";
  const m = h / 100;
  if (m <= 0) return "—";
  return (w / (m * m)).toFixed(1);
}

export default function MyPage() {
  const { data: me, isLoading: meLoading } = useMe();
  const { data: pet } = useMyPet();
  const { data: balance } = usePointBalance(0);
  const { data: xp } = useWeeklyXp();
  const { data: profile } = useQuery({
    queryKey: ["health-profile"],
    queryFn: fetchHealthProfileDetail,
    staleTime: 60_000,
  });
  const { logout } = useAuth();

  // 복약 관리 localStorage에서 복용중인 약 이름 목록 읽기
  const [medNames, setMedNames] = useState<string[]>([]);
  useEffect(() => {
    try {
      const raw = localStorage.getItem(MEDICATION_STORAGE_KEY);
      const list: Medication[] = raw ? JSON.parse(raw) : [];
      setMedNames(list.filter((m) => m.active).map((m) => m.name));
    } catch { /* 무시 */ }
  }, []);

  const birth = me?.birthday ?? me?.birth_date;
  const age = calcAge(birth);
  const bmi = calcBmi(profile?.height_cm, profile?.weight_kg);

  return (
    <div className="max-w-2xl mx-auto px-5 py-6 space-y-5">
      {/* 프로필 카드 */}
      <section className="bg-white border border-border rounded-[16px] p-5 flex items-center gap-4 shadow-sm">
        {/* 아바타 */}
        <div className="w-20 h-20 rounded-full bg-brand flex items-center justify-center text-2xl font-black shrink-0 overflow-hidden">
          {resolveMediaUrl(me?.avatar_url) ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={resolveMediaUrl(me?.avatar_url)}
              alt="프로필 사진"
              className="w-full h-full object-cover"
            />
          ) : (
            (me?.nickname?.[0] ?? me?.name?.[0] ?? "U").toUpperCase()
          )}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-lg font-black text-text-primary truncate">
            {meLoading ? "…" : (me?.nickname ?? me?.name ?? "—")}
          </p>
          <p className="text-xs text-text-tertiary truncate">
            @{me?.name ?? "—"} · {me?.email}
          </p>
        </div>
        <Link
          href="/mypage/edit"
          className="shrink-0 text-xs font-semibold text-brand-black underline underline-offset-2"
        >
          편집
        </Link>
      </section>

      {/* 빠른 통계: 포인트 · 주간 EXP · 펫 레벨 */}
      <section className="grid grid-cols-3 gap-3">
        <div className="bg-white border border-border rounded-[14px] p-3 text-center">
          <p className="text-xs text-text-tertiary mb-1">포인트</p>
          <p className="text-lg font-black text-brand-black">
            {(balance?.balance ?? 0).toLocaleString()} P
          </p>
        </div>
        <Link
          href="/leaderboard"
          className="bg-white border border-border rounded-[14px] p-3 text-center hover:shadow-sm"
        >
          <p className="text-xs text-text-tertiary mb-1">이번 주 EXP</p>
          <p className="text-lg font-black text-brand-black">
            {(xp?.total_points ?? 0).toLocaleString()}
          </p>
        </Link>
        <div className="bg-white border border-border rounded-[14px] p-3 text-center">
          <p className="text-xs text-text-tertiary mb-1">펫</p>
          <p className="text-lg font-black text-brand-black">
            {pet ? `Lv.${pet.level}` : "없음"}
          </p>
        </div>
      </section>

      {/* 읽기 전용 기본 정보 */}
      <section className="bg-white border border-border rounded-[16px] p-5 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-sm font-bold text-text-primary">기본 정보</p>
          <span className="text-[10px] text-text-tertiary">수정 불가 항목</span>
        </div>
        <dl className="grid grid-cols-2 gap-y-2 text-sm">
          <dt className="text-text-tertiary">이름</dt>
          <dd className="text-text-primary text-right">{me?.name ?? "—"}</dd>
          <dt className="text-text-tertiary">닉네임</dt>
          <dd className="text-text-primary text-right">
            {me?.nickname ?? "—"}
            <Link href="/mypage/edit" className="ml-2 text-[11px] text-brand-black underline">
              변경
            </Link>
          </dd>
          <dt className="text-text-tertiary">이메일</dt>
          <dd className="text-text-primary text-right truncate">
            {me?.email ?? "—"}
          </dd>
          <dt className="text-text-tertiary">성별</dt>
          <dd className="text-text-primary text-right">
            {genderLabel(me?.gender)}
          </dd>
          <dt className="text-text-tertiary">생년월일</dt>
          <dd className="text-text-primary text-right">{birth ?? "—"}</dd>
          <dt className="text-text-tertiary">휴대폰</dt>
          <dd className="text-text-primary text-right">
            {me?.phone_number ?? "—"}
            <Link
              href="/mypage/edit"
              className="ml-2 text-[11px] text-brand-black underline"
            >
              변경
            </Link>
          </dd>
        </dl>
      </section>

      {/* 건강 프로필 요약 */}
      <section className="bg-white border border-border rounded-[16px] p-5 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-sm font-bold text-text-primary">건강 프로필</p>
          <Link
            href="/health-records"
            className="text-xs font-semibold text-brand-black underline"
          >
            상세 보기
          </Link>
        </div>
        <dl className="grid grid-cols-2 gap-y-2 text-sm">
          <dt className="text-text-tertiary">나이</dt>
          <dd className="text-text-primary text-right">
            {age !== null ? `${age}세` : "—"}
          </dd>
          <dt className="text-text-tertiary">성별</dt>
          <dd className="text-text-primary text-right">
            {genderLabel(me?.gender)}
          </dd>
          <dt className="text-text-tertiary">키</dt>
          <dd className="text-text-primary text-right">
            {profile?.height_cm ? `${profile.height_cm} cm` : "—"}
          </dd>
          <dt className="text-text-tertiary">몸무게</dt>
          <dd className="text-text-primary text-right">
            {profile?.weight_kg ? `${profile.weight_kg} kg` : "—"}
          </dd>
          <dt className="text-text-tertiary">BMI</dt>
          <dd className="text-text-primary text-right">{bmi}</dd>
          <dt className="text-text-tertiary">보유 질환</dt>
          <dd className="text-text-primary text-right">
            {(() => {
              const diseases =
                profile?.diseases ?? profile?.chronic_diseases ?? [];
              return diseases.length > 0 ? diseases.join(", ") : "없음";
            })()}
          </dd>
          <dt className="text-text-tertiary">복용중인 약</dt>
          <dd className="text-text-primary text-right">
            {medNames.length > 0 ? medNames.join(", ") : "없음"}
          </dd>
          <dt className="text-text-tertiary">가족력</dt>
          <dd className="text-text-primary text-right">
            {[
              profile?.family_hp === 1 || profile?.has_hypertension_family_history === true
                ? "고혈압"
                : null,
              profile?.family_dm === 1 || profile?.has_diabetes_family_history === true
                ? "당뇨"
                : null,
              profile?.family_hl === 1 ? "고지혈증" : null,
            ]
              .filter(Boolean)
              .join(", ") || "없음"}
          </dd>
        </dl>
      </section>

      {/* 복약 관리 */}
      <MedicationManager />

      {/* 도메인 링크 */}
      <section className="bg-white border border-border rounded-[16px] overflow-hidden">
        {[
          { href: "/mypage/edit", label: "프로필 편집", icon: "✏️" },
          { href: "/mypage/password", label: "비밀번호 변경", icon: "🔒" },
          { href: "/mypage/display-settings", label: "화면 설정", icon: "🖥️" },
          { href: "/mypage/notification-settings", label: "알림 설정", icon: "🔔" },
          { href: "/mypage/invitations", label: "받은 초대", icon: "📨" },
          { href: "/mypage/points", label: "포인트 내역", icon: "💰" },
          { href: "/attendance", label: "출석 체크", icon: "📅" },
          { href: "/leaderboard", label: "주간 리더보드", icon: "🏆" },
          { href: "/support", label: "고객지원", icon: "🎧" },
          { href: "/withdrawal", label: "회원 탈퇴", icon: "🗑️" },
        ].map((it) => (
          <Link
            key={it.href}
            href={it.href}
            className="flex items-center justify-between px-5 py-3 border-b border-border last:border-b-0 hover:bg-surface"
          >
            <span className="flex items-center gap-2 text-sm text-text-primary">
              <span aria-hidden="true">{it.icon}</span>
              {it.label}
            </span>
            <span className="text-text-tertiary">›</span>
          </Link>
        ))}
        <button
          type="button"
          onClick={() => logout()}
          className="w-full flex items-center justify-between px-5 py-3 hover:bg-surface text-left"
        >
          <span className="flex items-center gap-2 text-sm text-status-error font-semibold">
            <span aria-hidden="true">↩️</span>
            로그아웃
          </span>
          <span className="text-text-tertiary">›</span>
        </button>
      </section>
    </div>
  );
}
