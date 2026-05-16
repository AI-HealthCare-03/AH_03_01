"use client";

/* =========================================
   3등분 빠른 진입 카드 컨테이너
   A: 내 현황, B: 출석, C: 건강 퀴즈
   ========================================= */

import MyStatusCard from "./MyStatusCard";
import AttendanceCard from "./AttendanceCard";
import HealthQuizCard from "./HealthQuizCard";
import type { MyPet, ChallengeItem, AttendanceMonthResponse } from "@/types/api";

interface QuickEntryGridProps {
  pet: MyPet | null | undefined;
  challenges: ChallengeItem[];
  petLoading: boolean;
  attendance: AttendanceMonthResponse | undefined;
  attendanceLoading: boolean;
}

export default function QuickEntryGrid({
  pet,
  challenges,
  petLoading,
  attendance,
  attendanceLoading,
}: QuickEntryGridProps) {
  return (
    <section aria-label="빠른 진입" className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <MyStatusCard
        pet={pet}
        challenges={challenges}
        isLoading={petLoading}
      />
      <AttendanceCard
        data={attendance}
        isLoading={attendanceLoading}
      />
      <HealthQuizCard />
    </section>
  );
}
