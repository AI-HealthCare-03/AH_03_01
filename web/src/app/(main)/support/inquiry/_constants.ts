import type { InquiryCategory, InquiryStatus } from "@/types/support";

export const CATEGORY_LABEL: Record<InquiryCategory, string> = {
  SERVICE_INQUIRY: "서비스 문의",
  ACCOUNT_INQUIRY: "계정 문의",
  ERROR_REPORT: "오류 신고",
  SANCTIONS_INQUIRY: "제재 문의",
  ETC: "기타",
};

export const STATUS_LABEL: Record<InquiryStatus, string> = {
  PENDING: "답변 대기",
  ANSWERED: "답변 완료",
};

export const STATUS_STYLE: Record<InquiryStatus, string> = {
  PENDING: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300",
  ANSWERED: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
};
