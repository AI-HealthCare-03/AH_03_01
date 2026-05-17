"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import Button from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import PetCharacter, { type PetStyle } from "@/components/pets/PetCharacter";
import {
  createPet,
  STYLE_TO_TYPE,
  type CreatePetRequest,
  type PetStyleKey,
} from "@/lib/api/pets";
import { MY_PET_QUERY_KEY } from "@/hooks/queries/useMyPet";
import { extractErrorMessage } from "@/lib/api/client";

/* =========================================
   펫 생성 — 종류 선택 + 이름 입력
   ========================================= */

interface Choice {
  style: PetStyleKey;
  label: string;
  species: string;
  description: string;
}

const CHOICES: Choice[] = [
  {
    style: "MALTIPOO",
    label: "강아지",
    species: "말티푸",
    description: "곱슬곱슬 친화력 좋은 강아지",
  },
  {
    style: "RAGDOLL",
    label: "고양이",
    species: "랙돌",
    description: "푸른 눈동자의 부드러운 고양이",
  },
  {
    style: "SUCCULENT",
    label: "식물",
    species: "다육이",
    description: "느긋하게 자라는 통통한 다육이",
  },
];

export default function PetCreatePage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [selected, setSelected] = useState<PetStyleKey>("MALTIPOO");
  const [name, setName] = useState("");

  const mutation = useMutation({
    mutationFn: (body: CreatePetRequest) => createPet(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MY_PET_QUERY_KEY });
      showToast("새 친구가 합류했어요!", "success");
      router.push("/pets");
    },
    onError: (err) => {
      showToast(extractErrorMessage(err), "error");
    },
  });

  const handleSubmit = () => {
    const trimmed = name.trim();
    if (trimmed.length < 1) {
      showToast("이름을 입력해 주세요", "info");
      return;
    }
    mutation.mutate({
      name: trimmed,
      pet_type: STYLE_TO_TYPE[selected],
      selected_style: selected,
    });
  };

  return (
    <div className="max-w-md mx-auto px-5 py-6 space-y-6">
      <div>
        <Link
          href="/pets"
          className="text-sm text-text-tertiary hover:text-text-secondary inline-block mb-3"
        >
          ← 펫
        </Link>
        <h1 className="text-xl font-black text-text-primary">새 친구 맞이하기</h1>
        <p className="text-sm text-text-secondary mt-1">
          한 마리만 키울 수 있으니 신중히 선택해 주세요
        </p>
      </div>

      {/* 미리보기 */}
      <div className="bg-surface rounded-[16px] py-8 flex items-center justify-center">
        <PetCharacter style={selected} size={140} bouncing />
      </div>

      {/* 종류 선택 */}
      <div className="grid grid-cols-3 gap-3">
        {CHOICES.map((c) => {
          const isSelected = c.style === selected;
          return (
            <button
              key={c.style}
              type="button"
              onClick={() => setSelected(c.style)}
              aria-pressed={isSelected}
              className={[
                "flex flex-col items-center gap-1 p-3 rounded-[14px] border-2 transition-colors",
                isSelected
                  ? "border-brand-black bg-brand/10"
                  : "border-border bg-white hover:border-text-secondary",
              ].join(" ")}
            >
              <div className="scale-75 -my-3">
                <PetCharacter style={c.style} size={56} />
              </div>
              <span className="text-xs font-bold text-text-primary">
                {c.label}
              </span>
              <span className="text-[11px] text-text-tertiary">{c.species}</span>
            </button>
          );
        })}
      </div>

      {/* 선택한 종류 안내 */}
      <p className="text-xs text-text-secondary text-center -mt-1">
        {CHOICES.find((c) => c.style === selected)?.description}
      </p>

      {/* 이름 */}
      <div>
        <label
          htmlFor="pet-name"
          className="text-xs font-semibold text-text-secondary mb-1 block"
        >
          이름 <span className="text-text-tertiary font-normal">(1~20자)</span>
        </label>
        <input
          id="pet-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={20}
          placeholder="예: 콩이"
          className="w-full px-3 py-2.5 rounded-[10px] border border-border focus:border-brand-black focus:outline-none text-sm"
        />
      </div>

      <Button
        variant="primary"
        size="lg"
        fullWidth
        loading={mutation.isPending}
        onClick={handleSubmit}
      >
        함께하기
      </Button>
    </div>
  );
}
