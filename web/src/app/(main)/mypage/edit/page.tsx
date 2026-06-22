"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { useMe, ME_QUERY_KEY } from "@/hooks/queries/useMe";
import { updateMe } from "@/lib/api/user";
import type { UpdateMeRequest } from "@/lib/api/user";
import { uploadFile } from "@/lib/api/files";
import { resolveMediaUrl } from "@/lib/api/media";
import { extractErrorMessage } from "@/lib/api/client";
import { checkNicknameAvailable } from "@/lib/api/auth";
import { formatPhoneNumber } from "@/lib/validators";

/* =========================================
   마이페이지 - 프로필 편집
   수정 가능: 닉네임(중복확인) / 휴대폰 / 프로필 사진
   비밀번호 변경: /mypage/password 페이지로 이동
   ========================================= */

const MAX_AVATAR_SIZE = 500 * 1024; /* 500KB */
const ALLOWED_AVATAR_MIME = ["image/png", "image/jpeg"];

type DuplStatus = "idle" | "checking" | "available" | "taken" | "mine";

export default function MyPageEditPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { data: me, isLoading } = useMe();

  const [nickname, setNickname] = useState("");
  const [phone, setPhone] = useState("");
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [avatarFileId, setAvatarFileId] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [nicknameDupl, setNicknameDupl] = useState<DuplStatus>("idle");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  /* 초기값 세팅 */
  useEffect(() => {
    if (me) {
      setNickname(me.nickname ?? "");
      setPhone(me.phone_number ?? "");
      setAvatarPreview(resolveMediaUrl(me.avatar_url) ?? null);
      setAvatarFileId(me.avatar_file_id ?? null);
    }
  }, [me]);

  /* 아바타 업로드 */
  const handleAvatarSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (!ALLOWED_AVATAR_MIME.includes(file.type)) {
      showToast("PNG 또는 JPG 만 업로드 가능합니다", "error");
      return;
    }
    if (file.size > MAX_AVATAR_SIZE) {
      showToast("최대 500KB 까지 업로드 가능합니다", "error");
      return;
    }
    setUploading(true);
    try {
      const uploaded = await uploadFile(file, "profile");
      setAvatarFileId(uploaded.id);
      setAvatarPreview(resolveMediaUrl(uploaded.access_url) ?? null);
      showToast("이미지를 업로드했어요. 저장하면 반영됩니다.", "info");
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    } finally {
      setUploading(false);
    }
  };

  /* 닉네임 중복 확인 */
  const handleNicknameDuplCheck = async () => {
    const trimmed = nickname.trim();
    if (!trimmed) {
      showToast("닉네임을 먼저 입력해 주세요", "info");
      return;
    }
    /* 현재 닉네임과 동일하면 별도 확인 불필요 */
    if (trimmed === (me?.nickname ?? "")) {
      showToast("현재 사용 중인 닉네임이에요", "info");
      setNicknameDupl("mine");
      return;
    }
    setNicknameDupl("checking");
    try {
      const res = await checkNicknameAvailable(trimmed);
      setNicknameDupl(res.available ? "available" : "taken");
      showToast(
        res.available ? "사용 가능한 닉네임이에요" : "이미 사용 중인 닉네임입니다",
        res.available ? "success" : "error",
      );
    } catch (err) {
      setNicknameDupl("idle");
      showToast(extractErrorMessage(err), "error");
    }
  };

  const updateMutation = useMutation({
    mutationFn: (body: UpdateMeRequest) => updateMe(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ME_QUERY_KEY });
      showToast("프로필이 저장되었어요", "success");
      router.push("/mypage");
    },
    onError: (err) => {
      showToast(extractErrorMessage(err), "error");
    },
  });

  const handleSave = () => {
    if (!me) return;
    const body: UpdateMeRequest = {};
    const trimmedNickname = nickname.trim();

    /* 닉네임이 변경된 경우 중복 확인 필수 */
    if (trimmedNickname && trimmedNickname !== (me.nickname ?? "")) {
      if (nicknameDupl !== "available") {
        showToast("닉네임 중복 확인이 필요해요", "error");
        return;
      }
      body.nickname = trimmedNickname;
    }
    if (phone.trim() && phone.trim() !== me.phone_number) body.phone_number = phone.trim();
    if (avatarFileId && avatarFileId !== me.avatar_file_id) body.avatar_file_id = avatarFileId;

    if (Object.keys(body).length === 0) {
      showToast("변경된 내용이 없어요", "info");
      return;
    }
    updateMutation.mutate(body);
  };

  if (isLoading) {
    return (
      <div className="max-w-md mx-auto px-5 py-6 space-y-4">
        <div className="h-8 w-32 bg-surface rounded animate-pulse" />
        <div className="h-32 bg-surface rounded animate-pulse" />
        <div className="h-12 bg-surface rounded animate-pulse" />
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto px-5 py-6 space-y-6">
      {/* 헤더 */}
      <div>
        <Link
          href="/mypage"
          className="text-sm text-text-tertiary hover:text-text-secondary inline-block mb-3"
        >
          ← 마이페이지
        </Link>
        <h1 className="text-xl font-black text-text-primary">프로필 편집</h1>
        <p className="text-sm text-text-secondary mt-1">
          닉네임 · 휴대폰 · 프로필 사진을 변경할 수 있어요
        </p>
      </div>

      {/* 아바타 업로드 */}
      <div className="flex flex-col items-center gap-3">
        <div className="w-24 h-24 rounded-full bg-brand flex items-center justify-center text-3xl font-black overflow-hidden">
          {avatarPreview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={avatarPreview}
              alt="프로필 사진 미리보기"
              className="w-full h-full object-cover"
            />
          ) : (
            (nickname[0] ?? me?.name?.[0] ?? "U").toUpperCase()
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg"
          className="hidden"
          onChange={handleAvatarSelect}
        />
        <Button
          variant="outline"
          size="sm"
          loading={uploading}
          onClick={() => fileInputRef.current?.click()}
        >
          사진 변경
        </Button>
        <p className="text-[11px] text-text-tertiary text-center">
          PNG 또는 JPG · 최대 500KB
        </p>
      </div>

      {/* 폼 */}
      <div className="space-y-4">
        {/* 닉네임 + 중복 확인 */}
        <div className="space-y-1.5">
          <label
            htmlFor="nickname"
            className="text-xs font-semibold text-text-secondary block"
          >
            닉네임 <span className="text-text-tertiary font-normal">(2~10자)</span>
          </label>
          <div className="flex gap-2">
            <input
              id="nickname"
              type="text"
              value={nickname}
              onChange={(e) => {
                setNickname(e.target.value);
                setNicknameDupl("idle"); /* 값 바뀌면 확인 초기화 */
              }}
              maxLength={10}
              className="flex-1 px-3 py-2.5 rounded-[10px] border border-border focus:border-brand-black focus:outline-none text-sm"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              loading={nicknameDupl === "checking"}
              onClick={handleNicknameDuplCheck}
              className="shrink-0"
            >
              중복 확인
            </Button>
          </div>
          {nicknameDupl === "available" && (
            <p className="text-xs text-status-success">✓ 사용 가능한 닉네임이에요</p>
          )}
          {nicknameDupl === "mine" && (
            <p className="text-xs text-status-info">현재 사용 중인 닉네임이에요</p>
          )}
          {nicknameDupl === "taken" && (
            <p className="text-xs text-status-danger">이미 사용 중인 닉네임입니다</p>
          )}
        </div>

        {/* 휴대폰 번호 */}
        <div>
          <label
            htmlFor="phone"
            className="text-xs font-semibold text-text-secondary mb-1 block"
          >
            휴대폰 번호
          </label>
          <input
            id="phone"
            type="tel"
            value={phone}
            onChange={(e) => setPhone(formatPhoneNumber(e.target.value))}
            placeholder="010-1234-5678"
            className="w-full px-3 py-2.5 rounded-[10px] border border-border focus:border-brand-black focus:outline-none text-sm"
          />
        </div>
      </div>

      {/* 비밀번호 변경 */}
      <div className="flex items-center justify-between px-4 py-3 border border-border rounded-[12px]">
        <div>
          <p className="text-sm font-semibold text-text-primary">비밀번호</p>
          <p className="text-xs text-text-tertiary mt-0.5">
            보안을 위해 주기적으로 변경해 주세요
          </p>
        </div>
        <Link href="/mypage/password">
          <Button variant="outline" size="sm">
            변경하기
          </Button>
        </Link>
      </div>

      {/* 수정 불가 안내 */}
      <div className="bg-status-info-bg rounded-[12px] px-4 py-3">
        <p className="text-xs text-status-info leading-relaxed">
          이름·이메일·성별·생년월일은 변경할 수 없어요. 변경이 필요하면
          고객센터에 문의해 주세요.
        </p>
      </div>

      {/* 저장 */}
      <Button
        variant="primary"
        size="lg"
        fullWidth
        loading={updateMutation.isPending}
        onClick={handleSave}
      >
        저장
      </Button>
    </div>
  );
}
