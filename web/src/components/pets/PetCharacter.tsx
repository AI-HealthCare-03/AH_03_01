"use client";

import type { CSSProperties } from "react";
import { useEffect, useState } from "react";

/* =========================================
   펫 캐릭터 — 3종 모두 PNG 시퀀스 (public/pets/{dog,cat,plant}/*.png).
   rembg 로 누끼 처리된 RGBA 이미지를 사용한다.

   facing : 좌/우/정/뒤. LEFT 면 좌우 mirroring.
   sick   : true → sick.png (mood 무시)
   moving : true → walking_1 ↔ walking_2 교차 (200ms)
   mood   : 표정/감정. idle → idle ↔ idle_2 blink (1500ms)
   ========================================= */

export type PetStyle = "MALTIPOO" | "RAGDOLL" | "SUCCULENT";
export type PetFacing = "FRONT" | "LEFT" | "RIGHT" | "BACK";
export type PetMood = "idle" | "happy" | "sleepy" | "sleeping" | "sad";
export type PetVariant = "ribbon" | "flower" | null;

interface PetCharacterProps {
  style: PetStyle;
  facing?: PetFacing;
  size?: number; // px, default 96
  bouncing?: boolean;
  sick?: boolean;
  moving?: boolean;
  mood?: PetMood;
  variant?: PetVariant; // 리본/꽃 꾸미기 → 스프라이트 교체 (강아지/고양이만)
  playing?: boolean; // 공놀이 시퀀스 재생 (강아지/고양이만)
}

/* 공놀이 프레임 순서 (folder 기준). 식물은 시퀀스 없음 → 미재생 */
const PLAY_FRAMES: Record<string, string[]> = {
  dog: [
    "play_with_ball",
    "play_with_ball_1",
    "play_with_ball_2",
    "play_with_ball_3",
    "play_with_ball_4",
    "play_with_ball_5",
  ],
  cat: ["play_with_ball", "play_with_ball_1", "play_with_ball_2", "play_with_ball_3"],
};

/* style → public 폴더 + alt 텍스트 */
const STYLE_INFO: Record<PetStyle, { folder: string; alt: string }> = {
  MALTIPOO: { folder: "dog", alt: "강아지" },
  RAGDOLL: { folder: "cat", alt: "고양이" },
  SUCCULENT: { folder: "plant", alt: "식물" },
};

export default function PetCharacter({
  style,
  facing = "FRONT",
  size = 96,
  bouncing = false,
  sick = false,
  moving = false,
  mood = "idle",
  variant = null,
  playing = false,
}: PetCharacterProps) {
  /* walking PNG 가 오른쪽 향한 측면 자세로 생성됨.
     - LEFT: scaleX(-1) 로 좌우 mirror
     - 그 외: identity */
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
        <PetPng
          style={style}
          size={size}
          sick={sick}
          moving={moving}
          mood={mood}
          variant={variant}
          playing={playing}
        />
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

function PetPng({
  style,
  size,
  sick,
  moving,
  mood,
  variant,
  playing,
}: {
  style: PetStyle;
  size: number;
  sick: boolean;
  moving: boolean;
  mood: PetMood;
  variant: PetVariant;
  playing: boolean;
}) {
  const { folder, alt } = STYLE_INFO[style];
  const [frame, setFrame] = useState(0);
  useEffect(() => {
    const interval = moving ? 200 : 1500;
    const t = setInterval(() => setFrame((f) => 1 - f), interval);
    return () => clearInterval(t);
  }, [moving]);

  /* 공놀이 시퀀스 — 강아지/고양이만, playing 동안 프레임 순환 */
  const playFrames = PLAY_FRAMES[folder];
  const canPlay = playing && !!playFrames;
  const [playIdx, setPlayIdx] = useState(0);
  useEffect(() => {
    if (!canPlay) {
      setPlayIdx(0);
      return;
    }
    const t = setInterval(() => setPlayIdx((i) => (i + 1) % playFrames.length), 160);
    return () => clearInterval(t);
  }, [canPlay, playFrames]);

  const base = `/pets/${folder}`;
  let name: string;
  if (canPlay) name = playFrames[playIdx];
  else if (sick) name = "sick";
  else if (mood === "sad") name = "sad";
  else if (mood === "happy") name = "happy";
  else if (mood === "sleeping") name = "sleeping";
  else if (mood === "sleepy") name = "sleepy";
  else if (moving) name = frame === 0 ? "walking_1" : "walking_2";
  else name = frame === 0 ? "idle" : "idle_2";

  /* 리본/꽃 꾸미기 → 스프라이트 교체. 식물·공놀이 프레임에는 미적용 */
  const useVariant = !!variant && folder !== "plant" && !canPlay;
  const fileName = useVariant ? `${name}_${variant}` : name;
  const src = `${base}/${fileName}.png`;

  return (
    /* eslint-disable-next-line @next/next/no-img-element */
    <img
      src={src}
      alt={alt}
      width={size}
      height={size}
      draggable={false}
      style={{ display: "block", width: size, height: size, objectFit: "contain" }}
    />
  );
}
