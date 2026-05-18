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
   펫 키우기 메인 화면 v3 (대형 무대 + placement 기반 장착)
   - placement: head|paws → 펫 추적 (펫 div 안 배치)
   - placement: stage_top → 우상단 고정
   - placement: stage_bottom → 무대에 자유 배치(드래그 가능, localStorage 저장)
   - 별이 빛나는 밤 배경 → 별 패턴 SVG 추가
   ========================================= */

const STAGE_W = 800;
const STAGE_H = 480;
const PET_W = 160;
const PET_H = 160;
const FURN_PX = 56; // 가구 emoji 박스 크기
const SPEED = 18; // px / keystroke

const SPEECH_BY_STYLE: Record<PetStyle, string[]> = {
  MALTIPOO: ["멍!", "꼬리 살랑살랑", "산책 가자!", "맛있는 거 어디?", "졸려…"],
  RAGDOLL: ["야옹~", "그르릉…", "쓰담쓰담 좋아", "어딜 가?", "낮잠 잘래"],
  SUCCULENT: ["햇볕 좋다", "물 한 모금", "쑥쑥 자라는 중", "흙이 부드러워", "쉬는 중…"],
};

const SICK_SPEECH_BY_STYLE: Record<PetStyle, string[]> = {
  MALTIPOO: ["기운이 없어…", "끙…", "쉬고 싶어"],
  RAGDOLL: ["골골… 안 좋아", "잠만 자고 싶어", "쉬익…"],
  SUCCULENT: ["잎이 시들…", "물 좀…", "햇볕 부족"],
};

function styleFor(pet: { pet_type?: string; selected_style?: string | null }): PetStyle {
  const s = pet.selected_style;
  if (s === "MALTIPOO" || s === "RAGDOLL" || s === "SUCCULENT") return s;
  if (pet.pet_type === "CAT") return "RAGDOLL";
  if (pet.pet_type === "PLANT") return "SUCCULENT";
  return "MALTIPOO";
}

interface EquippedSlotItem {
  id: number;
  name: string;
  emoji?: string | null;
  slot?: string | null;
  placement?: string | null;
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

  /* 드래그 가능한 가구의 위치를 itemId 별로 보관. localStorage 영속화. */
  const [furniturePos, setFurniturePos] = useState<Record<number, { x: number; y: number }>>({});
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const dragOffset = useRef({ x: 0, y: 0 });

  useEffect(() => {
    try {
      const raw = localStorage.getItem("hr_furniture_pos");
      if (raw) setFurniturePos(JSON.parse(raw));
    } catch {
      /* ignore */
    }
  }, []);

  const persistFurnPos = useCallback((next: Record<number, { x: number; y: number }>) => {
    setFurniturePos(next);
    try {
      localStorage.setItem("hr_furniture_pos", JSON.stringify(next));
    } catch {
      /* ignore */
    }
  }, []);

  const style = pet ? styleFor(pet as { pet_type?: string; selected_style?: string | null }) : "MALTIPOO";
  const sick = !!(pet as { sick?: boolean } | null | undefined)?.sick;
  const equipped = pet as
    | {
        equipped_background?: { id: number; name: string; gradient?: string | null } | null;
        equipped_furniture?: EquippedSlotItem[];
        equipped_decoration?: EquippedSlotItem[];
      }
    | null
    | undefined;
  const equippedBg = equipped?.equipped_background ?? null;
  const equippedFurn = equipped?.equipped_furniture ?? [];
  const equippedDeco = equipped?.equipped_decoration ?? [];

  /* placement 분류 — 없으면 카테고리 기본값(furniture=stage_bottom, decoration=stage_top) */
  const headItems = equippedDeco.filter((d) => d.placement === "head");
  const stageTopItems = equippedDeco.filter((d) => d.placement !== "head");
  const pawItems = equippedFurn.filter((f) => f.placement === "paws");
  const stageBottomItems = equippedFurn.filter((f) => f.placement !== "paws");

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
      setMoving(true);
      if (movingTimer.current) clearTimeout(movingTimer.current);
      movingTimer.current = setTimeout(() => setMoving(false), 250);
      setMood((m) => (m === "sleepy" || m === "sleeping" ? "idle" : m));
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [pet, sayRandom]);

  /* 일정 시간 미입력 → sleepy/sleeping */
  useEffect(() => {
    if (!pet || sick) return;
    const sleepyT = setTimeout(() => setMood((m) => (m === "idle" ? "sleepy" : m)), 50_000);
    const sleepingT = setTimeout(() => setMood((m) => (m === "idle" || m === "sleepy" ? "sleeping" : m)), 120_000);
    return () => {
      clearTimeout(sleepyT);
      clearTimeout(sleepingT);
    };
  }, [pet, sick, position, speech]);

  useEffect(() => {
    if (!pet) return;
    const interval = setInterval(() => sayRandom(), 12_000);
    return () => clearInterval(interval);
  }, [pet, sayRandom]);

  /* ─── 가구 드래그 핸들러 (마우스/터치 통합 pointer 이벤트) ─── */
  const onFurnPointerDown = (id: number) => (e: React.PointerEvent<HTMLDivElement>) => {
    e.stopPropagation();
    e.preventDefault();
    const stage = stageRef.current?.getBoundingClientRect();
    if (!stage) return;
    const cur = furniturePos[id] ?? defaultFurnitureSpot(id, stageBottomItems);
    dragOffset.current = {
      x: e.clientX - stage.left - cur.x,
      y: e.clientY - stage.top - cur.y,
    };
    setDraggingId(id);
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
  };

  useEffect(() => {
    if (draggingId === null) return;
    const move = (e: PointerEvent) => {
      const stage = stageRef.current?.getBoundingClientRect();
      if (!stage) return;
      /* 무대의 표시 크기(stage) 기준 좌표 → STAGE_W/H 도메인으로 변환 */
      const scaleX = STAGE_W / stage.width;
      const scaleY = STAGE_H / stage.height;
      const x = (e.clientX - stage.left - dragOffset.current.x) * scaleX;
      const y = (e.clientY - stage.top - dragOffset.current.y) * scaleY;
      const clampedX = Math.max(0, Math.min(STAGE_W - FURN_PX, x));
      const clampedY = Math.max(0, Math.min(STAGE_H - FURN_PX, y));
      setFurniturePos((prev) => ({ ...prev, [draggingId]: { x: clampedX, y: clampedY } }));
    };
    const up = () => {
      setDraggingId((id) => {
        if (id !== null) {
          setFurniturePos((prev) => {
            persistFurnPos(prev);
            return prev;
          });
        }
        return null;
      });
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
    };
  }, [draggingId, persistFurnPos]);

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto px-5 py-6">
        <div className="h-96 bg-surface rounded-[16px] animate-pulse" />
      </div>
    );
  }

  if (!pet) {
    return (
      <div className="max-w-md mx-auto px-5 py-10 text-center space-y-5">
        <PetCharacter style="MALTIPOO" size={160} bouncing />
        <div>
          <h1 className="text-xl font-black text-text-primary mb-1">아직 친구가 없어요</h1>
          <p className="text-sm text-text-secondary">
            강아지·고양이·식물 중에서 함께할 친구를 골라 보세요
          </p>
        </div>
        <Link href="/pets/create">
          <Button variant="primary" size="lg">친구 데려오기</Button>
        </Link>
      </div>
    );
  }

  const isNightSky = equippedBg?.name === "별이 빛나는 밤";
  const isDefaultBg = !equippedBg || equippedBg.name === "맑은 하늘";

  return (
    <div className="max-w-5xl mx-auto px-3 sm:px-5 py-4 space-y-4">
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
            방향키 / WASD · 스페이스: 말 걸기 · 가구 드래그 OK
          </span>
        </div>
      </div>

      {sick && (
        <div className="inline-flex items-center gap-1 bg-red-50 text-red-700 text-xs font-semibold rounded-full px-2.5 py-1">
          <span aria-hidden="true">🤒</span>
          <span>아픔</span>
        </div>
      )}

      {/* 무대 — 화면 가득 (반응형, 비율 유지) */}
      <div
        ref={stageRef}
        tabIndex={0}
        role="application"
        aria-label="펫 키우기 무대"
        onClick={sayRandom}
        className="relative rounded-[20px] overflow-hidden focus:outline-none focus:ring-2 focus:ring-brand mx-auto select-none"
        style={{
          width: "100%",
          aspectRatio: `${STAGE_W} / ${STAGE_H}`,
          background:
            equippedBg?.gradient ||
            "linear-gradient(to bottom, #FFF6D6 0%, #FFE9A8 60%, #C8E6A0 60%, #A6D88B 100%)",
          filter: sick ? "brightness(0.92) saturate(0.85)" : undefined,
          touchAction: draggingId !== null ? "none" : undefined,
        }}
      >
        {/* 별이 빛나는 밤 — 별 패턴 SVG */}
        {isNightSky && <NightStars />}

        {/* 기본 배경(맑은 하늘) — 구름/해/잔디 */}
        {isDefaultBg && (
          <>
            <Cloud x={60} y={32} />
            <Cloud x={510} y={64} />
            <Cloud x={300} y={40} />
            <div
              aria-hidden="true"
              className="absolute"
              style={{
                top: "3%",
                right: "3%",
                width: "8%",
                aspectRatio: "1 / 1",
                borderRadius: "50%",
                background: "#FFD24A",
              }}
            />
            <Grass x={40} y={400} />
            <Grass x={200} y={430} />
            <Grass x={420} y={415} />
            <Grass x={620} y={440} />
            <Grass x={720} y={420} />
          </>
        )}

        {/* DECORATION (stage_top) — 우측 상단 */}
        {stageTopItems.map((d, i) => (
          <div
            key={d.id}
            aria-hidden="true"
            className="absolute"
            style={{
              top: 16 + i * 56,
              right: 20 + i * 6,
              fontSize: 48,
              lineHeight: 1,
            }}
          >
            {d.emoji}
          </div>
        ))}

        {/* FURNITURE (stage_bottom) — 사용자 드래그 가능 */}
        {stageBottomItems.map((f, idx) => {
          const spot = furniturePos[f.id] ?? defaultFurnitureSpot(f.id, stageBottomItems, idx);
          const stage = stageRef.current?.getBoundingClientRect();
          const scaleX = stage ? stage.width / STAGE_W : 1;
          const scaleY = stage ? stage.height / STAGE_H : 1;
          return (
            <div
              key={f.id}
              onPointerDown={onFurnPointerDown(f.id)}
              onClick={(e) => e.stopPropagation()}
              role="button"
              aria-label={`${f.name} 드래그`}
              className="absolute cursor-grab active:cursor-grabbing"
              style={{
                left: spot.x * scaleX,
                top: spot.y * scaleY,
                fontSize: 64,
                lineHeight: 1,
                userSelect: "none",
                transition: draggingId === f.id ? "none" : "left 200ms ease, top 200ms ease",
              }}
              title={`${f.name} (드래그로 이동)`}
            >
              {f.emoji}
            </div>
          );
        })}

        {/* 펫 (+ 머리 위 꽃/리본 + 발 앞 공) */}
        <div
          className="absolute"
          style={{
            left: `${(position.x / STAGE_W) * 100}%`,
            top: `${(position.y / STAGE_H) * 100}%`,
            width: `${(PET_W / STAGE_W) * 100}%`,
            aspectRatio: `${PET_W} / ${PET_H}`,
            transition: "left 120ms ease, top 120ms ease",
          }}
        >
          {/* 머리 위 장식 (꽃/리본) — 펫보다 약간 위, 가운데 정렬, 한 개당 좌우 살짝 어긋 */}
          {headItems.map((d, i) => (
            <div
              key={d.id}
              aria-hidden="true"
              className="absolute"
              style={{
                top: "-18%",
                left: `${42 + i * 14}%`,
                fontSize: 44,
                lineHeight: 1,
                transform: "rotate(-12deg)",
                pointerEvents: "none",
              }}
            >
              {d.emoji}
            </div>
          ))}

          <PetCharacter
            style={style}
            facing={facing}
            size={PET_W}
            sick={sick}
            moving={moving}
            mood={mood}
          />

          {/* 발 앞 (공 같은) — 펫 하단 약간 앞쪽 */}
          {pawItems.map((f) => (
            <div
              key={f.id}
              aria-hidden="true"
              className="absolute"
              style={{
                bottom: "-4%",
                left: facing === "LEFT" ? "-10%" : "70%",
                fontSize: 36,
                lineHeight: 1,
                pointerEvents: "none",
              }}
            >
              {f.emoji}
            </div>
          ))}

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
            : "무대를 클릭하거나 스페이스를 누르면 친구가 한 마디 해요. 가방의 배경·가구·꾸미기를 사용하면 무대가 꾸며져요. 가구는 마우스로 드래그해 위치를 옮길 수 있어요."}
        </p>
      </div>
    </div>
  );
}

/* 무대 좌표계(STAGE_W×STAGE_H) 안에서 가구의 기본 위치를 좌→우로 분산 */
function defaultFurnitureSpot(
  id: number,
  list: EquippedSlotItem[],
  givenIdx?: number,
): { x: number; y: number } {
  const idx = givenIdx ?? list.findIndex((it) => it.id === id);
  const safeIdx = idx < 0 ? 0 : idx;
  const x = 80 + safeIdx * 180;
  const y = STAGE_H - 110;
  return { x, y };
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
      style={{ left: `${(x / STAGE_W) * 100}%`, top: `${(y / STAGE_H) * 100}%`, width: "12%" }}
      viewBox="0 0 64 28"
      preserveAspectRatio="xMidYMid meet"
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
      style={{ left: `${(x / STAGE_W) * 100}%`, top: `${(y / STAGE_H) * 100}%`, width: "3%" }}
      viewBox="0 0 20 24"
      preserveAspectRatio="xMidYMid meet"
    >
      <path d="M 10 24 Q 6 12 4 4" stroke="#5DAA48" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      <path d="M 10 24 Q 10 14 10 6" stroke="#5DAA48" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      <path d="M 10 24 Q 14 12 16 4" stroke="#5DAA48" strokeWidth="1.6" fill="none" strokeLinecap="round" />
    </svg>
  );
}

/* 별이 빛나는 밤 — 작은 별 점들 + 큰 별 + 초승달 */
function NightStars() {
  const stars = Array.from({ length: 80 }, (_, i) => {
    /* 결정론적 의사난수 (i 기반) — 매 렌더마다 위치 안 바뀜 */
    const x = ((i * 73) % 1000) / 10; // 0~100
    const y = ((i * 137) % 700) / 10; // 0~70 (상단 위주)
    const r = 0.5 + ((i * 31) % 12) / 10; // 0.5~1.7
    const o = 0.6 + ((i * 53) % 40) / 100; // 0.6~1.0
    return { x, y, r, o };
  });
  return (
    <svg
      aria-hidden="true"
      className="absolute inset-0 w-full h-full pointer-events-none"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
    >
      {stars.map((s, i) => (
        <circle key={i} cx={s.x} cy={s.y} r={s.r * 0.25} fill="#FFF8C8" opacity={s.o}>
          {i % 7 === 0 && (
            <animate attributeName="opacity" values={`${s.o};0.2;${s.o}`} dur={`${2 + (i % 4)}s`} repeatCount="indefinite" />
          )}
        </circle>
      ))}
      {/* 큰 반짝이 별 */}
      <g transform="translate(82,18)" fill="#FFF8C8">
        <path d="M0 -3 L0.8 -0.8 L3 0 L0.8 0.8 L0 3 L-0.8 0.8 L-3 0 L-0.8 -0.8 Z" />
      </g>
      <g transform="translate(15,32)" fill="#FFF8C8">
        <path d="M0 -2 L0.6 -0.6 L2 0 L0.6 0.6 L0 2 L-0.6 0.6 L-2 0 L-0.6 -0.6 Z" />
      </g>
      {/* 초승달 */}
      <g transform="translate(88,10)">
        <circle cx="0" cy="0" r="4" fill="#FFF1B0" />
        <circle cx="-1.5" cy="-0.7" r="3.6" fill="#0E1B3A" />
      </g>
    </svg>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  const safe = Math.max(0, Math.min(100, value));
  return (
    <div className="bg-white border border-border rounded-[14px] p-3">
      <p className="text-xs text-text-tertiary mb-1">{label}</p>
      <div className="h-2 bg-surface rounded-full overflow-hidden mb-1">
        <div className="h-full bg-brand rounded-full transition-all" style={{ width: `${safe}%` }} />
      </div>
      <p className="text-[11px] text-right text-text-secondary">{safe}</p>
    </div>
  );
}
