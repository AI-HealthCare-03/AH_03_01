import apiClient from "./client";
import type {
  FAQCategory,
  FAQItem,
  InquiryListItem,
  InquiryDetail,
  InquiryCreateRequest,
  InquiryUpdateRequest,
} from "@/types/support";

export async function getFAQs(params?: { category?: FAQCategory }): Promise<FAQItem[]> {
  const res = await apiClient.get<FAQItem[]>("/api/v1/support/faqs", { params });
  return res.data;
}

export async function listInquiries(params?: {
  offset?: number;
  limit?: number;
}): Promise<InquiryListItem[]> {
  const res = await apiClient.get<InquiryListItem[]>("/api/v1/support/inquiries", { params });
  return res.data;
}

export async function createInquiry(data: InquiryCreateRequest): Promise<InquiryDetail> {
  const res = await apiClient.post<InquiryDetail>("/api/v1/support/inquiries", data);
  return res.data;
}

export async function getInquiry(id: number): Promise<InquiryDetail> {
  const res = await apiClient.get<InquiryDetail>(`/api/v1/support/inquiries/${id}`);
  return res.data;
}

export async function updateInquiry(id: number, data: InquiryUpdateRequest): Promise<InquiryDetail> {
  const res = await apiClient.patch<InquiryDetail>(`/api/v1/support/inquiries/${id}`, data);
  return res.data;
}

export async function deleteInquiry(id: number): Promise<void> {
  await apiClient.delete(`/api/v1/support/inquiries/${id}`);
}
