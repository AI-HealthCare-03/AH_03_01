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

interface PetCharacterProps {
  style: PetStyle;
  facing?: PetFacing;
  size?: number; // px, default 96
  bouncing?: boolean;
  sick?: boolean;
  moving?: boolean;
  mood?: PetMood;
}

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
        <PetPng style={style} size={size} sick={sick} moving={moving} mood={mood} />
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
}: {
  style: PetStyle;
  size: number;
  sick: boolean;
  moving: boolean;
  mood: PetMood;
}) {
  const { folder, alt } = STYLE_INFO[style];
  const [frame, setFrame] = useState(0);
  useEffect(() => {
    const interval = moving ? 200 : 1500;
    const t = setInterval(() => setFrame((f) => 1 - f), interval);
    return () => clearInterval(t);
  }, [moving]);

  const base = `/pets/${folder}`;
  let src = `${base}/idle.png`;
  if (sick) src = `${base}/sick.png`;
  else if (mood === "sad") src = `${base}/sad.png`;
  else if (mood === "happy") src = `${base}/happy.png`;
  else if (mood === "sleeping") src = `${base}/sleeping.png`;
  else if (mood === "sleepy") src = `${base}/sleepy.png`;
  else if (moving) src = frame === 0 ? `${base}/walking_1.png` : `${base}/walking_2.png`;
  else src = frame === 0 ? `${base}/idle.png` : `${base}/idle_2.png`;

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
