"use client";

/* =========================================
   랭킹 카드 컴포넌트
   ========================================= */

interface LeaderboardCardProps {
  rank: number;
  name: string;
  exp: number;
  completedChallenges: number;
  isMe?: boolean;
}

interface RankStyle {
  bg: string;
  textColor: string;
  emoji: string;
}

const RANK_STYLE: Record<number, RankStyle> = {
  1: { bg: "rank-card-gold bg-yellow-50 border-yellow-300", textColor: "text-yellow-600", emoji: "🥇" },
  2: { bg: "rank-card-silver bg-gray-50 border-gray-300", textColor: "text-gray-500", emoji: "🥈" },
  3: { bg: "rank-card-bronze bg-orange-50 border-orange-300", textColor: "text-orange-500", emoji: "🥉" },
};

export default function LeaderboardCard({
  rank,
  name,
  exp,
  completedChallenges,
  isMe = false,
}: LeaderboardCardProps) {
  const style: RankStyle | undefined = RANK_STYLE[rank];

  return (
    <div
      className={[
        "flex items-center gap-3 p-4 rounded-[14px] border-2 transition-all",
        style ? style.bg : "bg-white border-border",
        isMe ? "border-brand-black shadow-md" : "",
      ].join(" ")}
      aria-current={isMe ? "true" : undefined}
    >
      {/* 순위 */}
      <div className="w-10 text-center shrink-0">
        {style ? (
          <span className="text-2xl" aria-label={`${rank}위`} aria-hidden="false">
            {style.emoji}
          </span>
        ) : (
          <span className="text-base font-black text-text-tertiary">
            {rank}
          </span>
        )}
      </div>

      {/* 아바타 */}
      <div
        className={[
          "w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold shrink-0",
          isMe ? "bg-brand text-brand-black" : "bg-surface text-text-secondary",
        ].join(" ")}
      >
        {name.charAt(0).toUpperCase()}
      </div>

      {/* 이름 + EXP */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-bold text-text-primary truncate">{name}</p>
          {isMe && (
            <span className="text-[10px] font-bold px-1.5 py-0.5 bg-brand rounded text-brand-black shrink-0">
              나
            </span>
          )}
        </div>
        <p className="text-xs text-text-tertiary">
          챌린지 {completedChallenges}개 완료
        </p>
      </div>

      {/* EXP */}
      <div className="text-right shrink-0">
        <p className="text-base font-black text-text-primary">
          {exp.toLocaleString()}
        </p>
        <p className="text-[10px] text-text-tertiary">EXP</p>
      </div>
    </div>
  );
}
