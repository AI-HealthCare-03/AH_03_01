export type FAQCategory = "ACCOUNT" | "CHALLENGE" | "HEALTH_DATA" | "REWARD";
export type InquiryCategory =
  | "SERVICE_INQUIRY"
  | "ACCOUNT_INQUIRY"
  | "ERROR_REPORT"
  | "SANCTIONS_INQUIRY"
  | "ETC";
export type InquiryStatus = "PENDING" | "ANSWERED";

export interface FAQItem {
  id: number;
  question: string;
  answer: string;
  category: FAQCategory;
  order: number;
}

export interface InquiryAnswer {
  id: number;
  content: string;
  created_at: string;
}

export interface InquiryListItem {
  id: number;
  title: string;
  category: InquiryCategory;
  status: InquiryStatus;
  created_at: string;
  updated_at: string;
}

export interface InquiryDetail extends InquiryListItem {
  content: string;
  attachment_url: string | null;
  answer: InquiryAnswer | null;
}

export interface InquiryCreateRequest {
  title: string;
  content: string;
  category: InquiryCategory;
  attachment_file_id?: number | null;
}

export interface InquiryUpdateRequest {
  title?: string;
  content?: string;
}
