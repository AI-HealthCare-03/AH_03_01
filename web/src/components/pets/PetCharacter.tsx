"use client";

import type { CSSProperties } from "react";

/* =========================================
   펫 캐릭터 (말티푸/랙돌/다육이)
   저작권 회피 위해 SVG 로 직접 그린 신규 캐릭터.
   facing: 마주보는 방향 (좌/우/정/뒤) — 방향키 이동 시 좌우 mirroring 적용.
   ========================================= */

export type PetStyle = "MALTIPOO" | "RAGDOLL" | "SUCCULENT";
export type PetFacing = "FRONT" | "LEFT" | "RIGHT" | "BACK";

interface PetCharacterProps {
  style: PetStyle;
  facing?: PetFacing;
  size?: number; // px, default 96
  bouncing?: boolean;
}

export default function PetCharacter({
  style,
  facing = "FRONT",
  size = 96,
  bouncing = false,
}: PetCharacterProps) {
  /* 방향키 좌 → 캐릭터를 좌측을 향하도록 좌우 반전 */
  const transform: CSSProperties = {
    transform: facing === "LEFT" ? "scaleX(-1)" : undefined,
    transition: "transform 120ms ease",
  };
  const wrap: CSSProperties = bouncing
    ? { animation: "petBounce 600ms infinite" }
    : {};

  return (
    <div style={wrap} aria-label={`펫 ${style}`}>
      <div style={transform}>
        {style === "MALTIPOO" ? (
          <Maltipoo size={size} />
        ) : style === "RAGDOLL" ? (
          <Ragdoll size={size} />
        ) : (
          <Succulent size={size} />
        )}
      </div>
      <style jsx>{`
        @keyframes petBounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-6px); }
        }
      `}</style>
    </div>
  );
}

/* ─── 말티푸 (강아지) ───────────────────────────
   동그란 머리 + 양쪽 늘어진 곱슬 귀 + 둥근 코.
   원작 캐릭터를 따라가지 않은 단순 일러스트. */
function Maltipoo({ size }: { size: number }) {
  return (
    <svg viewBox="0 0 100 100" width={size} height={size}>
      {/* 그림자 */}
      <ellipse cx="50" cy="92" rx="22" ry="3" fill="#000" opacity="0.1" />
      {/* 몸통 */}
      <ellipse cx="50" cy="70" rx="24" ry="18" fill="#F4E9D8" />
      {/* 머리 */}
      <circle cx="50" cy="44" r="26" fill="#F8F1E4" />
      {/* 귀 - 곱슬 */}
      <ellipse cx="24" cy="46" rx="11" ry="16" fill="#D9C8A8" />
      <ellipse cx="76" cy="46" rx="11" ry="16" fill="#D9C8A8" />
      <circle cx="20" cy="40" r="4" fill="#E5D5B8" />
      <circle cx="80" cy="40" r="4" fill="#E5D5B8" />
      {/* 눈 */}
      <circle cx="40" cy="42" r="3" fill="#3A2A1A" />
      <circle cx="60" cy="42" r="3" fill="#3A2A1A" />
      <circle cx="41" cy="41" r="1" fill="#FFF" />
      <circle cx="61" cy="41" r="1" fill="#FFF" />
      {/* 코 */}
      <ellipse cx="50" cy="52" rx="3" ry="2" fill="#3A2A1A" />
      {/* 입 */}
      <path d="M 46 56 Q 50 60 54 56" stroke="#3A2A1A" strokeWidth="1.5" fill="none" strokeLinecap="round" />
      {/* 볼터치 */}
      <circle cx="34" cy="52" r="3" fill="#FFB6C1" opacity="0.6" />
      <circle cx="66" cy="52" r="3" fill="#FFB6C1" opacity="0.6" />
      {/* 발 */}
      <ellipse cx="38" cy="86" rx="5" ry="4" fill="#E5D5B8" />
      <ellipse cx="62" cy="86" rx="5" ry="4" fill="#E5D5B8" />
    </svg>
  );
}

/* ─── 랙돌 (고양이) ─────────────────────────── */
function Ragdoll({ size }: { size: number }) {
  return (
    <svg viewBox="0 0 100 100" width={size} height={size}>
      <ellipse cx="50" cy="92" rx="22" ry="3" fill="#000" opacity="0.1" />
      {/* 몸통 */}
      <ellipse cx="50" cy="70" rx="22" ry="18" fill="#FAF2E6" />
      {/* 머리 */}
      <circle cx="50" cy="44" r="25" fill="#FDF6EA" />
      {/* 귀 - 세모 */}
      <polygon points="30,28 24,12 40,22" fill="#FDF6EA" />
      <polygon points="70,28 76,12 60,22" fill="#FDF6EA" />
      <polygon points="32,26 28,16 38,22" fill="#F2C8C0" />
      <polygon points="68,26 72,16 62,22" fill="#F2C8C0" />
      {/* 색깔 무늬 (코·귀끝) */}
      <ellipse cx="50" cy="52" rx="9" ry="7" fill="#E8D3C5" opacity="0.7" />
      {/* 눈 - 파란 눈 */}
      <ellipse cx="40" cy="42" rx="3.5" ry="4" fill="#4A90E2" />
      <ellipse cx="60" cy="42" rx="3.5" ry="4" fill="#4A90E2" />
      <ellipse cx="40" cy="42" rx="1" ry="3" fill="#1B2B40" />
      <ellipse cx="60" cy="42" rx="1" ry="3" fill="#1B2B40" />
      <circle cx="41" cy="41" r="0.8" fill="#FFF" />
      <circle cx="61" cy="41" r="0.8" fill="#FFF" />
      {/* 코 */}
      <path d="M 47 52 L 53 52 L 50 56 Z" fill="#E29CA3" />
      {/* 수염 */}
      <line x1="32" y1="55" x2="42" y2="56" stroke="#A89682" strokeWidth="0.8" />
      <line x1="32" y1="58" x2="42" y2="58" stroke="#A89682" strokeWidth="0.8" />
      <line x1="68" y1="55" x2="58" y2="56" stroke="#A89682" strokeWidth="0.8" />
      <line x1="68" y1="58" x2="58" y2="58" stroke="#A89682" strokeWidth="0.8" />
      {/* 입 */}
      <path d="M 46 58 Q 50 62 54 58" stroke="#3A2A1A" strokeWidth="1.5" fill="none" strokeLinecap="round" />
      {/* 발 */}
      <ellipse cx="38" cy="86" rx="5" ry="4" fill="#FAF2E6" />
      <ellipse cx="62" cy="86" rx="5" ry="4" fill="#FAF2E6" />
    </svg>
  );
}

/* ─── 다육이 (식물) ─────────────────────────── */
function Succulent({ size }: { size: number }) {
  return (
    <svg viewBox="0 0 100 100" width={size} height={size}>
      <ellipse cx="50" cy="92" rx="22" ry="3" fill="#000" opacity="0.1" />
      {/* 화분 */}
      <path d="M 28 70 L 32 92 L 68 92 L 72 70 Z" fill="#C98C6B" />
      <rect x="26" y="66" width="48" height="8" rx="2" fill="#B0744F" />
      {/* 흙 */}
      <ellipse cx="50" cy="68" rx="22" ry="4" fill="#5C4533" />
      {/* 잎 — 가운데 큰 잎 */}
      <ellipse cx="50" cy="50" rx="9" ry="20" fill="#7ABA6E" />
      <ellipse cx="50" cy="48" rx="6" ry="14" fill="#A6D89B" />
      {/* 좌측 잎 */}
      <g transform="rotate(-35 50 60)">
        <ellipse cx="50" cy="55" rx="7" ry="16" fill="#86C77B" />
        <ellipse cx="50" cy="53" rx="4.5" ry="10" fill="#B8DFAD" />
      </g>
      {/* 우측 잎 */}
      <g transform="rotate(35 50 60)">
        <ellipse cx="50" cy="55" rx="7" ry="16" fill="#86C77B" />
        <ellipse cx="50" cy="53" rx="4.5" ry="10" fill="#B8DFAD" />
      </g>
      {/* 눈 */}
      <circle cx="44" cy="52" r="2.2" fill="#1F3D1F" />
      <circle cx="56" cy="52" r="2.2" fill="#1F3D1F" />
      <circle cx="44.5" cy="51.4" r="0.6" fill="#FFF" />
      <circle cx="56.5" cy="51.4" r="0.6" fill="#FFF" />
      {/* 입 */}
      <path d="M 46 58 Q 50 61 54 58" stroke="#1F3D1F" strokeWidth="1.2" fill="none" strokeLinecap="round" />
      {/* 볼터치 */}
      <circle cx="40" cy="57" r="2.4" fill="#FFB6C1" opacity="0.7" />
      <circle cx="60" cy="57" r="2.4" fill="#FFB6C1" opacity="0.7" />
    </svg>
  );
}
