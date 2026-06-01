"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import Button from "@/components/ui/Button";
import { useMyPet } from "@/hooks/queries/useMyPet";
import PetCharacter, {
  type PetFacing,
  type PetMood,
  type PetStyle,
  type PetVariant,
} from "@/components/pets/PetCharacter";

/* =========================================
   펫 키우기 메인 화면 v4 (이미지 풀블리드 무대)
   - 배경: equipped_background.image(main|sunset|star|beach) → 가로/세로 반응형 이미지 풀블리드
   - 가구/소품(placement=stage_bottom): 이미지 PNG, 마우스 드래그로 위치 이동(% 좌표, localStorage)
   - 꾸미기:
       · ribbon/flower(pet_skin) → 펫 스프라이트 통째 교체 (강아지/고양이만)
       · ball(play) → 무대 클릭/스페이스로 공놀이 시퀀스 1회 재생
       · butterfly(stage_top) → 8프레임 나비 애니메이션 오버레이
   - 좌표는 무대(콘텐츠 영역) 대비 백분율. 세이프존 안에서만 이동.
   ========================================= */

const PET_STEP = 3; // % / keystroke
// 펫/가구 이동 세이프존(%). 하늘로 못 올라가게 minY를 지면 위쪽으로 제한.
const SAFE = { minX: 10, maxX: 90, minY: 58, maxY: 86 };
const FURN_STORAGE_KEY = "hr_furniture_pos_v2";
const BG_SIZES = { wide: "2560_1440", portrait: "1080_1920", tall: "1290_2796" };

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
  asset?: string | null;
  variant?: string | null;
}

function clamp(v: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, v));
}

export default function PetsPage() {
  const { data: pet, isLoading } = useMyPet();
  const [position, setPosition] = useState({ x: 50, y: 62 }); // % (펫 중심)
  const [facing, setFacing] = useState<PetFacing>("FRONT");
  const [speech, setSpeech] = useState<string | null>(null);
  const [moving, setMoving] = useState(false);
  const [mood, setMood] = useState<PetMood>("idle");
  const [playing, setPlaying] = useState(false);
  const speechTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const movingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const moodTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const playTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);

  /* 드래그 가능한 가구의 위치(%)를 itemId 별로 보관. localStorage 영속화. */
  const [furniturePos, setFurniturePos] = useState<Record<number, { x: number; y: number }>>({});
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const dragOffset = useRef({ x: 0, y: 0 });

  useEffect(() => {
    try {
      const raw = localStorage.getItem(FURN_STORAGE_KEY);
      if (raw) setFurniturePos(JSON.parse(raw));
    } catch {
      /* ignore */
    }
  }, []);

  const persistFurnPos = useCallback((next: Record<number, { x: number; y: number }>) => {
    setFurniturePos(next);
    try {
      localStorage.setItem(FURN_STORAGE_KEY, JSON.stringify(next));
    } catch {
      /* ignore */
    }
  }, []);

  const style = pet ? styleFor(pet as { pet_type?: string; selected_style?: string | null }) : "MALTIPOO";
  const isPlant = style === "SUCCULENT";
  const sick = !!(pet as { sick?: boolean } | null | undefined)?.sick;
  const equipped = pet as
    | {
        equipped_background?: { id: number; name: string; gradient?: string | null; image?: string | null } | null;
        equipped_furniture?: EquippedSlotItem[];
        equipped_decoration?: EquippedSlotItem[];
      }
    | null
    | undefined;
  const equippedBg = equipped?.equipped_background ?? null;
  const equippedFurn = equipped?.equipped_furniture ?? [];
  const equippedDeco = equipped?.equipped_decoration ?? [];

  /* 꾸미기 분류 */
  // 리본/꽃 → 스프라이트 교체(최근 장착 우선). 식물은 무시.
  const skinVariant: PetVariant = (() => {
    if (isPlant) return null;
    for (let i = equippedDeco.length - 1; i >= 0; i--) {
      const v = equippedDeco[i].variant;
      if (v === "ribbon" || v === "flower") return v;
    }
    return null;
  })();
  const hasBall = !isPlant && equippedDeco.some((d) => d.variant === "ball");
  const butterflies = equippedDeco.filter((d) => d.variant === "butterfly");

  const triggerPlay = useCallback(() => {
    if (!hasBall) return;
    setPlaying(true);
    if (playTimer.current) clearTimeout(playTimer.current);
    playTimer.current = setTimeout(() => setPlaying(false), 1400);
  }, [hasBall]);

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
      triggerPlay();
    }
  }, [style, sick, triggerPlay]);

  /* 키보드 이동 */
  useEffect(() => {
    if (!pet) return;
    const handleKey = (e: KeyboardEvent) => {
      const k = e.key;
      let dx = 0;
      let dy = 0;
      if (k === "ArrowLeft" || k === "a" || k === "A") dx = -PET_STEP;
      else if (k === "ArrowRight" || k === "d" || k === "D") dx = PET_STEP;
      else if (k === "ArrowUp" || k === "w" || k === "W") dy = -PET_STEP;
      else if (k === "ArrowDown" || k === "s" || k === "S") dy = PET_STEP;
      else if (k === " " || k === "Enter") {
        e.preventDefault();
        sayRandom();
        return;
      } else return;
      e.preventDefault();
      setPosition((p) => ({
        x: clamp(p.x + dx, SAFE.minX, SAFE.maxX),
        y: clamp(p.y + dy, SAFE.minY, SAFE.maxY),
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

  /* ─── 가구 드래그(% 좌표, pointer 통합) ─── */
  const pointerPct = (e: { clientX: number; clientY: number }) => {
    const stage = stageRef.current?.getBoundingClientRect();
    if (!stage) return null;
    return {
      x: ((e.clientX - stage.left) / stage.width) * 100,
      y: ((e.clientY - stage.top) / stage.height) * 100,
    };
  };

  const onFurnPointerDown = (id: number, idx: number) => (e: React.PointerEvent<HTMLDivElement>) => {
    e.stopPropagation();
    e.preventDefault();
    const p = pointerPct(e);
    if (!p) return;
    const cur = furniturePos[id] ?? defaultFurnitureSpot(idx);
    dragOffset.current = { x: p.x - cur.x, y: p.y - cur.y };
    setDraggingId(id);
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
  };

  useEffect(() => {
    if (draggingId === null) return;
    const move = (e: PointerEvent) => {
      const p = pointerPct(e);
      if (!p) return;
      const x = clamp(p.x - dragOffset.current.x, SAFE.minX, SAFE.maxX);
      const y = clamp(p.y - dragOffset.current.y, SAFE.minY, SAFE.maxY);
      setFurniturePos((prev) => ({ ...prev, [draggingId]: { x, y } }));
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
          <p className="text-sm text-text-secondary">강아지·고양이·식물 중에서 함께할 친구를 골라 보세요</p>
        </div>
        <Link href="/pets/create">
          <Button variant="primary" size="lg">
            친구 데려오기
          </Button>
        </Link>
      </div>
    );
  }

  // 미장착 시 기본 배경은 main 이미지. gradient 만 있는 레거시 배경은 gradient 사용.
  const bgKey = equippedBg?.image ?? (equippedBg?.gradient ? null : "main");
  const bgGradient = !bgKey ? equippedBg?.gradient ?? null : null;

  return (
    /* 무대 — 콘텐츠 영역(헤더/탭바 제외) 꽉 채움 */
    <div
      ref={stageRef}
      tabIndex={0}
      role="application"
      aria-label="펫 키우기 무대"
      onClick={sayRandom}
      className="relative w-full h-[calc(100dvh-4rem)] overflow-hidden focus:outline-none select-none"
      style={{ touchAction: draggingId !== null ? "none" : undefined }}
    >
      {/* 배경 레이어 — 무대 전체 cover */}
      <div className="absolute inset-0" aria-hidden="true">
        {bgKey ? (
          <picture>
            <source media="(orientation: landscape)" srcSet={`/pets/items/${bgKey}_${BG_SIZES.wide}.png`} />
            <source media="(max-width: 430px)" srcSet={`/pets/items/${bgKey}_${BG_SIZES.tall}.png`} />
            <img
              src={`/pets/items/${bgKey}_${BG_SIZES.portrait}.png`}
              alt=""
              className="w-full h-full object-cover"
            />
          </picture>
        ) : (
          <div
            className="w-full h-full"
            style={{
              background:
                bgGradient ||
                "linear-gradient(to bottom, #FFF6D6 0%, #FFE9A8 60%, #C8E6A0 60%, #A6D88B 100%)",
            }}
          />
        )}
        {sick && <div className="absolute inset-0 bg-black/10" />}
      </div>

      {/* 나비 오버레이 (stage_top) */}
        {butterflies.map((b, i) => (
          <Butterfly key={b.id} index={i} />
        ))}

        {/* 가구/소품 (stage_bottom) — 드래그 가능 */}
        {equippedFurn.map((f, idx) => {
          const spot = furniturePos[f.id] ?? defaultFurnitureSpot(idx);
          return (
            <div
              key={f.id}
              onPointerDown={onFurnPointerDown(f.id, idx)}
              onClick={(e) => e.stopPropagation()}
              role="button"
              aria-label={`${f.name} 드래그`}
              className="absolute cursor-grab active:cursor-grabbing"
              style={{
                left: `${spot.x}%`,
                top: `${spot.y}%`,
                width: "clamp(64px, 11vw, 116px)",
                transform: "translate(-50%, -50%)",
                transition: draggingId === f.id ? "none" : "left 180ms ease, top 180ms ease",
                touchAction: "none",
              }}
              title={`${f.name} (드래그로 이동)`}
            >
              {f.asset ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img src={f.asset} alt={f.name} draggable={false} className="w-full h-auto block select-none" />
              ) : (
                <span style={{ fontSize: 56, lineHeight: 1 }}>{f.emoji}</span>
              )}
            </div>
          );
        })}

        {/* 펫 */}
        <div
          className="absolute"
          style={{
            left: `${position.x}%`,
            top: `${position.y}%`,
            width: "clamp(120px, 20vw, 200px)",
            transform: "translate(-50%, -50%)",
            transition: "left 120ms ease, top 120ms ease",
          }}
        >
          <PetCharacter
            style={style}
            facing={facing}
            size={200}
            sick={sick}
            moving={moving}
            mood={mood}
            variant={skinVariant}
            playing={playing}
          />
          {speech && <SpeechBubble text={speech} />}
        </div>

        {/* ── 오버레이 UI ── */}
        {/* 좌상단: 이름/레벨 */}
        <div className="absolute top-3 left-3 md:top-5 md:left-5 z-10 rounded-[14px] bg-white/85 backdrop-blur px-3 py-2 shadow-sm">
          <h1 className="text-base font-black text-text-primary leading-tight">{pet.name}</h1>
          <p className="text-[11px] text-text-tertiary">
            Lv.{pet.level} · {pet.current_xp.toLocaleString()} EXP
          </p>
          {sick && (
            <span className="mt-1 inline-flex items-center gap-1 bg-red-50 text-red-700 text-[11px] font-semibold rounded-full px-2 py-0.5">
              <span aria-hidden="true">🤒</span> 아픔
            </span>
          )}
        </div>

        {/* 우상단: 상점/가방 */}
        <div className="absolute top-3 right-3 md:top-5 md:right-5 z-10 flex gap-2">
          <IconLink href="/pets/store" src="/pets/items/icon_store.png" label="상점" />
          <IconLink href="/pets/inventory" src="/pets/items/icon_bag.png" label="가방" />
        </div>

        {/* 하단: 상태 + 안내 */}
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 z-10 w-[min(92%,560px)] space-y-2">
          <div className="grid grid-cols-3 gap-2">
            <Stat label="배고픔" value={pet.hunger ?? 80} />
            <Stat label="청결" value={pet.cleanliness ?? 80} />
            <Stat label="기분" value={pet.mood ?? 80} />
          </div>
          <p className="text-center text-[11px] text-white drop-shadow-[0_1px_2px_rgba(0,0,0,0.6)]">
            {sick
              ? "가방의 회복약을 사용하면 회복할 수 있어요."
              : hasBall
                ? "방향키/WASD 이동 · 무대를 누르면 공놀이! · 가구는 드래그로 이동"
                : "방향키/WASD 이동 · 무대를 누르면 한 마디 · 가구는 드래그로 이동"}
          </p>
        </div>
    </div>
  );
}

/* 가구 기본 위치(%)를 좌→우 하단으로 분산 */
function defaultFurnitureSpot(idx: number): { x: number; y: number } {
  return { x: clamp(20 + idx * 16, SAFE.minX, SAFE.maxX), y: 80 };
}

function IconLink({ href, src, label }: { href: string; src: string; label: string }) {
  return (
    <Link
      href={href}
      aria-label={label}
      title={label}
      className="flex flex-col items-center justify-center w-12 h-12 rounded-[14px] bg-white/85 backdrop-blur shadow-sm hover:bg-white transition-colors"
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt="" className="w-7 h-7 object-contain" draggable={false} />
      <span className="text-[9px] font-semibold text-text-secondary leading-none mt-0.5">{label}</span>
    </Link>
  );
}

/* 8프레임 나비 애니메이션 + 살랑 이동 */
function Butterfly({ index }: { index: number }) {
  const [frame, setFrame] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setFrame((f) => (f + 1) % 8), 120);
    return () => clearInterval(t);
  }, []);
  const top = 12 + (index % 3) * 8;
  const left = 18 + index * 22;
  return (
    <div
      aria-hidden="true"
      className="absolute pointer-events-none"
      style={{
        top: `${top}%`,
        left: `${left}%`,
        width: "clamp(48px, 8vw, 84px)",
        animation: `butterflyDrift 6s ease-in-out ${index * 0.7}s infinite`,
      }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={`/pets/items/butterfly_${frame + 1}.png`} alt="" className="w-full h-auto block" draggable={false} />
      <style jsx>{`
        @keyframes butterflyDrift {
          0%,
          100% {
            transform: translate(0, 0);
          }
          25% {
            transform: translate(18px, -14px);
          }
          50% {
            transform: translate(-10px, 10px);
          }
          75% {
            transform: translate(12px, 6px);
          }
        }
      `}</style>
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

function Stat({ label, value }: { label: string; value: number }) {
  const safe = Math.max(0, Math.min(100, value));
  return (
    <div className="bg-white/85 backdrop-blur rounded-[12px] px-2.5 py-1.5 shadow-sm">
      <p className="text-[10px] text-text-tertiary mb-1">{label}</p>
      <div className="h-1.5 bg-surface rounded-full overflow-hidden mb-0.5">
        <div className="h-full bg-brand rounded-full transition-all" style={{ width: `${safe}%` }} />
      </div>
      <p className="text-[10px] text-right text-text-secondary">{safe}</p>
    </div>
  );
}
