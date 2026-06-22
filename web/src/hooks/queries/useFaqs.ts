import { useQuery } from "@tanstack/react-query";
import { fetchFaqs } from "@/lib/api/chat";

export const FAQS_KEY = "chat-faqs";

export function useFaqs(category?: string, keyword?: string) {
  return useQuery({
    queryKey: [FAQS_KEY, category, keyword],
    queryFn: () => fetchFaqs({ category, keyword }),
    staleTime: 1000 * 60 * 10, /* FAQ 는 10분 캐시 */
  });
}
