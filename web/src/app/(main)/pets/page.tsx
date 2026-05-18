"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import Button from "@/components/ui/Button";
import { useMyPet } from "@/hooks/queries/useMyPet";
import PetCharacter, {
  type PetFacing,
  type PetMood,
  type PetStyle,
} from "@/components/pets/PetCharacter";

/* =========================================
   펫 키우기 메인 화면
   - 펫 없으면 안내 → /pets/create
   - 펫 있으면 인터랙티브 무대:
     · 방향키(또는 WASD) 로 위치 이동
     · 클릭하면 말풍선으로 의사표현
     · 일정 시간 마다 자동으로 말풍선 변화
   ========================================= */

const STAGE_W = 480;
const STAGE_H = 320;
const PET_W = 120;
const PET_H = 120;
const SPEED = 14; // px / keystroke

/* 종류별 이모지·말풍선 사전 */
const SPEECH_BY_STYLE: Record<PetStyle, string[]> = {
  MALTIPOO: ["멍!", "꼬리 살랑살랑", "산책 가자!", "맛있는 거 어디?", "졸려…"],
  RAGDOLL: ["야옹~", "그르릉…", "쓰담쓰담 좋아", "어딜 가?", "낮잠 잘래"],
  SUCCULENT: ["햇볕 좋다", "물 한 모금", "쑥쑥 자라는 중", "흙이 부드러워", "쉬는 중…"],
};

/* sick(아픔) 상태일 때만 쓰는 말풍선 */
const SICK_SPEECH_BY_STYLE: Record<PetStyle, string[]> = {
  MALTIPOO: ["기운이 없어…", "끙…", "쉬고 싶어"],
  RAGDOLL: ["골골… 안 좋아", "잠만 자고 싶어", "쉬익…"],
  SUCCULENT: ["잎이 시들…", "물 좀…", "햇볕 부족"],
};

/* selected_style 값 매핑 — 백엔드에 없으면 pet_type 으로 폴백 */
function styleFor(pet: { pet_type?: string; selected_style?: string | null }): PetStyle {
  const s = pet.selected_style;
  if (s === "MALTIPOO" || s === "RAGDOLL" || s === "SUCCULENT") return s;
  if (pet.pet_type === "CAT") return "RAGDOLL";
  if (pet.pet_type === "PLANT") return "SUCCULENT";
  return "MALTIPOO";
}

export default function PetsPage() {
  const { data: pet, isLoading } = useMyPet();
  const [position, setPosition] = useState({ x: STAGE_W / 2 - PET_W / 2, y: STAGE_H / 2 - PET_H / 2 });
  const [facing, setFacing] = useState<PetFacing>("FRONT");
  const [speech, setSpeech] = useState<string | null>(null);
  const [moving, setMoving] = useState(false);
  const [mood, setMood] = useState<PetMood>("idle");
  const speechTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const movingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const moodTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);

  const style = pet ? styleFor(pet as { pet_type?: string; selected_style?: string | null }) : "MALTIPOO";
  const sick = !!(pet as { sick?: boolean } | null | undefined)?.sick;
  const equipped = pet as
    | {
        equipped_background?: { id: number; name: string; gradient?: string | null } | null;
        equipped_furniture?: { id: number; name: string; emoji?: string | null; slot?: string | null }[];
        equipped_decoration?: { id: number; name: string; emoji?: string | null }[];
      }
    | null
    | undefined;
  const equippedBg = equipped?.equipped_background ?? null;
  const equippedFurn = equipped?.equipped_furniture ?? [];
  const equippedDeco = equipped?.equipped_decoration ?? [];

  /* 말풍선 표시 (자동 사라짐) — sick 일 땐 sick 전용 풀에서 뽑음.
     말걸기 시 happy 표정으로 1.5초 잠깐 전환 (sick 이면 변경 안 함). */
  const sayRandom = useCallback(() => {
    const list = sick ? SICK_SPEECH_BY_STYLE[style] : SPEECH_BY_STYLE[style];
    const pick = list[Math.floor(Math.random() * list.length)];
    setSpeech(pick);
    if (speechTimer.current) clearTimeout(speechTimer.current);
    speechTimer.current = setTimeout(() => setSpeech(null), 2200);
    if (!sick) {
      setMood("happy");
      if (moodTimer.current) clearTimeout(moodTimer.current);
      moodTimer.current = setTimeout(() => setMood("idle"), 1500);
    }
  }, [style, sick]);

  /* 키보드 이동 */
  useEffect(() => {
    if (!pet) return;
    const handleKey = (e: KeyboardEvent) => {
      const k = e.key;
      let dx = 0;
      let dy = 0;
      if (k === "ArrowLeft" || k === "a" || k === "A") dx = -SPEED;
      else if (k === "ArrowRight" || k === "d" || k === "D") dx = SPEED;
      else if (k === "ArrowUp" || k === "w" || k === "W") dy = -SPEED;
      else if (k === "ArrowDown" || k === "s" || k === "S") dy = SPEED;
      else if (k === " " || k === "Enter") {
        e.preventDefault();
        sayRandom();
        return;
      } else return;
      e.preventDefault();
      setPosition((p) => ({
        x: Math.max(0, Math.min(STAGE_W - PET_W, p.x + dx)),
        y: Math.max(0, Math.min(STAGE_H - PET_H, p.y + dy)),
      }));
      if (dx < 0) setFacing("LEFT");
      else if (dx > 0) setFacing("RIGHT");
      else if (dy < 0) setFacing("BACK");
      else if (dy > 0) setFacing("FRONT");
      /* 마지막 키 입력 후 250ms 동안 walking 자세 유지 */
      setMoving(true);
      if (movingTimer.current) clearTimeout(movingTimer.current);
      movingTimer.current = setTimeout(() => setMoving(false), 250);
      /* 사용자 입력이 있었으므로 sleepy 상태 해제 */
      setMood((m) => (m === "sleepy" || m === "sleeping" ? "idle" : m));
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [pet, sayRandom]);

  /* 일정 시간 미입력 시 sleepy → sleeping 자동 전환 (sick 이면 변경 안 함). */
  useEffect(() => {
    if (!pet || sick) return;
    const sleepyT = setTimeout(() => {
      setMood((m) => (m === "idle" ? "sleepy" : m));
    }, 50_000);
    const sleepingT = setTimeout(() => {
      setMood((m) => (m === "idle" || m === "sleepy" ? "sleeping" : m));
    }, 120_000);
    return () => {
      clearTimeout(sleepyT);
      clearTimeout(sleepingT);
    };
  }, [pet, sick, position, speech]); // position/speech 변경(입력)마다 타이머 리셋

  /* 주기적인 자동 말풍선 (10~18초 간격) */
  useEffect(() => {
    if (!pet) return;
    const interval = setInterval(() => sayRandom(), 12_000);
    return () => clearInterval(interval);
  }, [pet, sayRandom]);

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto px-5 py-6">
        <div className="h-72 bg-surface rounded-[16px] animate-pulse" />
      </div>
    );
  }

  /* 펫 없음 → 생성 안내 */
  if (!pet) {
    return (
      <div className="max-w-md mx-auto px-5 py-10 text-center space-y-5">
        <PetCharacter style="MALTIPOO" size={160} bouncing />
        <div>
          <h1 className="text-xl font-black text-text-primary mb-1">
            아직 친구가 없어요
          </h1>
          <p className="text-sm text-text-secondary">
            강아지·고양이·식물 중에서 함께할 친구를 골라 보세요
          </p>
        </div>
        <Link href="/pets/create">
          <Button variant="primary" size="lg">
            친구 데려오기
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-5 py-6 space-y-5">
      {/* 헤더 */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-black text-text-primary">{pet.name}</h1>
          <p className="text-xs text-text-tertiary">
            Lv.{pet.level} · {pet.current_xp.toLocaleString()} EXP
          </p>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <div className="flex gap-2">
            <Link href="/pets/store" className="px-3 py-1.5 rounded-[10px] bg-surface text-xs font-semibold text-text-primary hover:bg-border">🛒 상점</Link>
            <Link href="/pets/inventory" className="px-3 py-1.5 rounded-[10px] bg-surface text-xs font-semibold text-text-primary hover:bg-border">🎒 가방</Link>
          </div>
          <span className="text-[11px] text-text-tertiary">
            방향키 / WASD · 스페이스: 말 걸기
          </span>
        </div>
      </div>

      {/* 아픔 배지 */}
      {sick && (
        <div className="inline-flex items-center gap-1 bg-red-50 text-red-700 text-xs font-semibold rounded-full px-2.5 py-1">
          <span aria-hidden="true">🤒</span>
          <span>아픔</span>
        </div>
      )}

      {/* 무대 */}
      <div
        ref={stageRef}
        tabIndex={0}
        role="application"
        aria-label="펫 키우기 무대"
        onClick={sayRandom}
        className="relative rounded-[20px] overflow-hidden focus:outline-none focus:ring-2 focus:ring-brand"
        style={{
          width: "100%",
          maxWidth: STAGE_W,
          height: STAGE_H,
          margin: "0 auto",
          background:
            equippedBg?.gradient ||
            "linear-gradient(to bottom, #FFF6D6 0%, #FFE9A8 60%, #C8E6A0 60%, #A6D88B 100%)",
          filter: sick ? "brightness(0.92) saturate(0.85)" : undefined,
        }}
      >
        {/* 기본 배경(맑은 하늘) 때만 구름/해/잔디를 그린다. 다른 배경은 그라데이션만 사용. */}
        {!equippedBg || equippedBg.name === "맑은 하늘" ? (
          <>
            <Cloud x={60} y={32} />
            <Cloud x={310} y={64} />
            <div
              aria-hidden="true"
              className="absolute"
              style={{ top: 12, right: 16, width: 36, height: 36, borderRadius: "50%", background: "#FFD24A" }}
            />
            <Grass x={40} y={220} />
            <Grass x={120} y={250} />
            <Grass x={260} y={235} />
            <Grass x={380} y={260} />
          </>
        ) : null}

        {/* DECORATION — 우측 상단에 이모지 배치 */}
        {equippedDeco.map((d, i) => (
          <div
            key={d.id}
            aria-hidden="true"
            className="absolute text-3xl"
            style={{ top: 14 + i * 36, right: 14 + i * 4 }}
          >
            {d.emoji}
          </div>
        ))}

        {/* FURNITURE — slot=left/right 기반 하단 배치 */}
        {equippedFurn.map((f) => (
          <div
            key={f.id}
            aria-hidden="true"
            className="absolute text-4xl"
            style={{
              bottom: 14,
              left: f.slot === "right" ? undefined : 24,
              right: f.slot === "right" ? 24 : undefined,
            }}
          >
            {f.emoji}
          </div>
        ))}

        {/* 펫 */}
        <div
          className="absolute select-none"
          style={{
            left: position.x,
            top: position.y,
            width: PET_W,
            height: PET_H,
            transition: "left 120ms ease, top 120ms ease",
          }}
        >
          <PetCharacter
            style={style}
            facing={facing}
            size={PET_W}
            sick={sick}
            moving={moving}
            mood={mood}
          />
          {/* 말풍선 */}
          {speech && <SpeechBubble text={speech} />}
        </div>
      </div>

      {/* 상태 카드 */}
      <div className="grid grid-cols-3 gap-3">
        <Stat label="배고픔" value={pet.hunger ?? 80} />
        <Stat label="청결" value={pet.cleanliness ?? 80} />
        <Stat label="기분" value={pet.mood ?? 80} />
      </div>

      {/* 하단 안내 */}
      <div className="bg-status-info-bg rounded-[12px] px-4 py-3">
        <p className="text-xs text-status-info leading-relaxed">
          {sick
            ? "약을 사용하면 회복할 수 있어요."
            : "무대를 클릭하거나 스페이스를 누르면 친구가 한 마디 해요. 가방에서 배경·가구·꾸미기 아이템을 사용하면 무대가 꾸며져요."}
        </p>
      </div>
    </div>
  );
}

function SpeechBubble({ text }: { text: string }) {
  return (
    <div
      className="absolute -top-2 left-1/2 -translate-x-1/2 -translate-y-full bg-white px-3 py-1.5 rounded-[14px] border border-border text-xs font-semibold text-text-primary shadow-sm whitespace-nowrap"
      role="status"
      aria-live="polite"
    >
      {text}
      <span
        aria-hidden="true"
        className="absolute left-1/2 -bottom-1 -translate-x-1/2 w-2 h-2 rotate-45 bg-white border-b border-r border-border"
      />
    </div>
  );
}

function Cloud({ x, y }: { x: number; y: number }) {
  return (
    <svg
      aria-hidden="true"
      className="absolute"
      style={{ left: x, top: y }}
      width="64"
      height="28"
      viewBox="0 0 64 28"
    >
      <ellipse cx="20" cy="18" rx="14" ry="8" fill="#fff" opacity="0.9" />
      <ellipse cx="38" cy="14" rx="16" ry="10" fill="#fff" opacity="0.9" />
      <ellipse cx="50" cy="20" rx="10" ry="6" fill="#fff" opacity="0.9" />
    </svg>
  );
}

function Grass({ x, y }: { x: number; y: number }) {
  return (
    <svg
      aria-hidden="true"
      className="absolute"
      style={{ left: x, top: y }}
      width="20"
      height="24"
      viewBox="0 0 20 24"
    >
      <path d="M 10 24 Q 6 12 4 4" stroke="#5DAA48" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      <path d="M 10 24 Q 10 14 10 6" stroke="#5DAA48" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      <path d="M 10 24 Q 14 12 16 4" stroke="#5DAA48" strokeWidth="1.6" fill="none" strokeLinecap="round" />
    </svg>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  const safe = Math.max(0, Math.min(100, value));
  return (
    <div className="bg-white border border-border rounded-[14px] p-3">
      <p className="text-xs text-text-tertiary mb-1">{label}</p>
      <div className="h-2 bg-surface rounded-full overflow-hidden mb-1">
        <div
          className="h-full bg-brand rounded-full transition-all"
          style={{ width: `${safe}%` }}
        />
      </div>
      <p className="text-[11px] text-right text-text-secondary">{safe}</p>
    </div>
  );
}
