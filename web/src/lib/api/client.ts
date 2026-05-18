import axios, {
  type AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from "axios";
import { API_BASE_URL, ROUTES } from "@/constants";
import { getToken, removeToken } from "@/lib/tokens";

/* =========================================
   Axios 클라이언트
   - NEXT_PUBLIC_API_BASE_URL 기반
   - 요청마다 Bearer 토큰 자동 첨부
   - 401 수신 시 토큰 삭제 + /login 리다이렉트
   ========================================= */

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15_000,
  headers: {
    "Content-Type": "application/json",
  },
});

/* 요청 인터셉터: Authorization 헤더 자동 첨부 + FormData 일 때 Content-Type 제거
   (axios 가 FormData 를 감지해 boundary 포함된 multipart/form-data 헤더를 자동 설정한다) */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    if (
      typeof FormData !== "undefined" &&
      config.data instanceof FormData
    ) {
      // 기본 Content-Type(application/json) 을 제거해 axios 가 boundary 를 자동 설정하게 한다.
      // setContentType(null) 도 AxiosHeaders 에서 동일하게 동작.
      delete (config.headers as Record<string, unknown>)["Content-Type"];
      delete (config.headers as Record<string, unknown>)["content-type"];
    }
    return config;
  },
  (error) => Promise.reject(error)
);

/* 응답 인터셉터: 에러 처리 */
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const status = error.response?.status;

    if (status === 401) {
      /* 인증 만료: 토큰 삭제 후 로그인 페이지로 */
      removeToken();
      if (typeof window !== "undefined") {
        window.location.href = ROUTES.LOGIN;
      }
    }

    /* TODO(backend): /api/v1/auth/token 으로 토큰 갱신 스텁
     * refresh_token 이 추가되면 여기서 silent refresh 구현
     */

    return Promise.reject(error);
  }
);

/* 응답 에러에서 사람이 읽을 수 있는 메시지 추출 */
export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data;
    if (!data) return "네트워크 오류가 발생했습니다";
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map((d: { msg: string }) => d.msg).join(", ");
    }
  }
  return "알 수 없는 오류가 발생했습니다";
}

/* 422 Validation 에러를 필드별 에러 맵으로 변환 */
export function extractFieldErrors(
  error: unknown
): Record<string, string> {
  if (axios.isAxiosError(error) && error.response?.status === 422) {
    const details = error.response.data?.detail;
    if (Array.isArray(details)) {
      return Object.fromEntries(
        details.map((d: { loc: (string | number)[]; msg: string }) => [
          d.loc[d.loc.length - 1],
          d.msg,
        ])
      );
    }
  }
  return {};
}

export default apiClient;
