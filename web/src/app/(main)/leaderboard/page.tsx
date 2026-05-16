"use client";

import Link from "next/link";
import LeaderboardCard from "@/components/challenges/ranking/LeaderboardCard";

/* =========================================
   주간 활동 랭킹 (10-C18 / 15-C06)
   백엔드 미구현 → 정적 mock 데이터
   ========================================= */

/* 정적 mock 데이터 */
const MOCK_RANKING = [
  { id: 1, name: "건강왕 김철수", exp: 3420, completedChallenges: 8 },
  { id: 2, name: "운동마니아 이영희", exp: 2980, completedChallenges: 7 },
  { id: 3, name: "습관왕 박민준", exp: 2650, completedChallenges: 6 },
  { id: 4, name: "꾸준함 최지은", exp: 2100, completedChallenges: 5 },
  { id: 5, name: "도전러 정현수", exp: 1850, completedChallenges: 4 },
  { id: 6, name: "나 (홍길동)", exp: 1520, completedChallenges: 3, isMe: true },
  { id: 7, name: "건강지킴이 윤서연", exp: 1340, completedChallenges: 3 },
  { id: 8, name: "꾸준기 이준호", exp: 980, completedChallenges: 2 },
  { id: 9, name: "루틴왕 강예림", exp: 750, completedChallenges: 2 },
  { id: 10, name: "첫걸음 이지수", exp: 430, completedChallenges: 1 },
] as const;

const ME_RANK = MOCK_RANKING.findIndex((r) => "isMe" in r && r.isMe) + 1;

export default function LeaderboardPage() {
  return (
    <div className="max-w-2xl mx-auto px-5 py-6 space-y-5">
      {/* 헤더 */}
      <div>
        <Link
          href="/challenges"
          className="text-sm text-text-tertiary hover:text-text-secondary mb-3 inline-block"
        >
          ← 챌린지로
        </Link>
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-black text-text-primary">주간 활동 랭킹</h1>
          <span className="text-xs font-medium text-status-info bg-status-info-bg px-2 py-1 rounded-full">
            매주 월요일 00:00 초기화
          </span>
        </div>
        <p className="text-sm text-text-secondary mt-1">
          이번 주 가장 열심히 활동한 멤버들이에요
        </p>
      </div>

      {/* 안내 배너: 정적 데이터 */}
      <div className="bg-status-warning-bg border border-status-warning rounded-[12px] px-4 py-3">
        <p className="text-xs font-semibold text-text-primary">
          현재 랭킹 데이터는 준비 중이에요
        </p>
        <p className="text-xs text-text-secondary mt-0.5">
          실시간 랭킹 기능은 곧 제공될 예정입니다. 아래는 예시 화면입니다.
        </p>
      </div>

      {/* 내 순위 */}
      <div className="bg-brand/10 border border-brand rounded-[14px] px-4 py-3">
        <p className="text-xs font-semibold text-text-secondary mb-1">내 순위</p>
        <div className="flex items-center justify-between">
          <p className="text-2xl font-black text-brand-black">
            {ME_RANK}위
          </p>
          <p className="text-sm font-semibold text-text-secondary">
            1,520 EXP
          </p>
        </div>
      </div>

      {/* 랭킹 목록 */}
      <div className="space-y-2">
        {MOCK_RANKING.map((entry, idx) => (
          <LeaderboardCard
            key={entry.id}
            rank={idx + 1}
            name={entry.name}
            exp={entry.exp}
            completedChallenges={entry.completedChallenges}
            isMe={"isMe" in entry && entry.isMe}
          />
        ))}
      </div>

      {/* EXP 획득 방식 안내 카드 */}
      <div className="bg-white border border-border rounded-[16px] p-5 shadow-sm">
        <p className="text-sm font-bold text-text-primary mb-3">
          경험치(EXP) 획득 방법
        </p>
        <ul className="space-y-2">
          {[
            { icon: "✅", text: "데일리 인증 완료", exp: "+50~100 EXP" },
            { icon: "🏆", text: "챌린지 완주", exp: "+200 EXP" },
            { icon: "🎯", text: "7일 연속 인증", exp: "+150 EXP 보너스" },
            { icon: "📅", text: "출석 체크", exp: "+10 EXP" },
          ].map((item) => (
            <li key={item.text} className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <span aria-hidden="true">{item.icon}</span>
                <span className="text-text-secondary">{item.text}</span>
              </span>
              <span className="font-semibold text-brand-black">{item.exp}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
