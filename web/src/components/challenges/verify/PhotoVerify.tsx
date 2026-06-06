"use client";

import { useState, useRef } from "react";
import Button from "@/components/ui/Button";
import { CATEGORY_CONFIG } from "@/components/challenges/common/ChallengeCategoryIcon";
import { useToast } from "@/components/ui/Toast";
import { uploadFile } from "@/lib/api/files";
import { extractErrorMessage } from "@/lib/api/client";
import type { Challenge } from "@/types/challenge";

/* =========================================
   사진 인증 컴포넌트 (10-C11)
   method=PHOTO 인증
   - 실제 multipart 업로드 → file_id → 챌린지 인증 호출
   - 업로드된 사진은 ai_worker 가 SigLIP2 zero-shot 으로 검증
   ========================================= */

interface PhotoVerifyProps {
  challenge: Challenge;
  onSubmit: (caption: string, photoFileId: number) => void;
  loading?: boolean;
}

export default function PhotoVerify({
  challenge,
  onSubmit,
  loading = false,
}: PhotoVerifyProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [caption, setCaption] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();

  const config = CATEGORY_CONFIG[challenge.category] ?? CATEGORY_CONFIG.EXERCISE;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    const reader = new FileReader();
    reader.onload = (ev) => {
      setPreview(ev.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleSubmit = async () => {
    if (!selectedFile) {
      showToast("사진을 먼저 선택해 주세요", "info");
      return;
    }
    setUploading(true);
    try {
      const uploaded = await uploadFile(selectedFile, "verification");
      onSubmit(caption, uploaded.id);
    } catch (err) {
      showToast(extractErrorMessage(err), "error");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="text-center">
        <span className="text-5xl" aria-hidden="true">
          {config.emoji}
        </span>
        <h2 className="text-lg font-black text-text-primary mt-3 mb-1">
          {config.label} 인증
        </h2>
        <p className="text-sm text-text-secondary">
          사진을 찍어 오늘의 달성을 기록해요
        </p>
      </div>

      {/* 사진 업로드 영역
          - input 은 DOM 에 숨겨두고 별도 "사진 선택" 버튼으로 트리거 (마이페이지 edit 과 동일 패턴)
          - 박스에 onClick 을 걸지 않아 자동 클릭이 발생하지 않도록 함 */}
      <div className="space-y-2">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          className="hidden"
          aria-label="인증 사진 선택"
          id="verify-photo-input"
        />
        <div
          className={[
            "block w-full aspect-video rounded-[16px] border-2 border-dashed overflow-hidden",
            "flex flex-col items-center justify-center",
            preview ? "border-brand-black" : "border-border",
          ].join(" ")}
        >
          {preview ? (
            /* eslint-disable-next-line @next/next/no-img-element */
            <img
              src={preview}
              alt="인증 사진 미리보기"
              className="w-full h-full object-cover rounded-[14px]"
            />
          ) : (
            <div className="text-center p-8">
              <span className="text-4xl block mb-3" aria-hidden="true">
                📸
              </span>
              <p className="text-sm font-semibold text-text-secondary">
                사진을 선택하거나 촬영하세요
              </p>
              <p className="text-xs text-text-tertiary mt-1">
                JPG, PNG 등 이미지 파일
              </p>
            </div>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          fullWidth
          onClick={() => fileInputRef.current?.click()}
        >
          {preview ? "다른 사진 선택" : "사진 선택"}
        </Button>
        {preview && (
          <button
            type="button"
            onClick={() => {
              setPreview(null);
              setSelectedFile(null);
              if (fileInputRef.current) fileInputRef.current.value = "";
            }}
            className="text-xs text-text-tertiary hover:text-text-secondary underline mx-auto block"
          >
            지우기
          </button>
        )}
      </div>

      {/* 메모 */}
      <div>
        <label
          htmlFor="verify-caption"
          className="block text-sm font-semibold text-text-primary mb-2"
        >
          한 마디 <span className="text-text-tertiary font-normal">(선택)</span>
        </label>
        <textarea
          id="verify-caption"
          value={caption}
          onChange={(e) => setCaption(e.target.value)}
          rows={3}
          maxLength={500}
          placeholder="오늘의 활동을 간단히 기록해보세요..."
          className="w-full px-4 py-3 rounded-[12px] border border-border text-sm resize-none focus:outline-none focus:border-brand-black"
        />
        <p className="text-xs text-text-tertiary text-right mt-1">
          {caption.length}/500
        </p>
      </div>

      {/* AI 검증 안내 */}
      <div className="bg-status-info-bg rounded-[12px] px-4 py-3">
        <p className="text-xs text-status-info leading-relaxed">
          <span className="font-bold">SigLIP2 AI</span> 가 카테고리({config.label})
          에 맞는 사진인지 자동으로 확인해요. 약 1~5초 정도 걸리며 결과는 자동으로
          반영됩니다.
        </p>
      </div>

      {/* 제출 */}
      <Button
        variant="primary"
        size="lg"
        fullWidth
        loading={loading || uploading}
        onClick={handleSubmit}
        disabled={!selectedFile}
      >
        {uploading ? "업로드 중…" : "인증 완료"}
      </Button>
    </div>
  );
}
