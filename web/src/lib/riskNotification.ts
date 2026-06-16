import { pushNotification } from "@/components/layout/NotificationDropdown";
import { notifRiskPollKey, riskLevelCacheKey } from "@/lib/notifKeys";
import type { RagPredictionItem } from "@/types/health";

const DISEASE_LABELS: Record<string, string> = {
  HYPERTENSION: "고혈압",
  DIABETES: "당뇨",
  CARDIOVASCULAR: "이상지질혈증",
};

const RISK_LABELS: Record<string, string> = {
  NORMAL: "정상",
  CAUTION: "주의",
  RISK: "위험",
  HIGH_RISK: "고위험",
};

/**
 * 이전 예측과 비교해 risk_level이 바뀐 질환만 위험도 알림 push.
 * localStorage(riskLevelCacheKey)를 비교 기준으로 사용하며 호출 후 캐시를 갱신한다.
 */
export function compareAndPushRiskNotifications(predictions: RagPredictionItem[]) {
  if (!predictions?.length) return;
  try {
    const prevRaw = localStorage.getItem(riskLevelCacheKey());
    const prevMap: Record<string, string> = prevRaw ? JSON.parse(prevRaw) : {};
    const nextMap: Record<string, string> = { ...prevMap };

    let pushed = false;
    for (const pred of predictions) {
      const prev = prevMap[pred.disease_type];
      if (prev && prev !== pred.risk_level) {
        pushNotification({
          category: "위험도",
          title: `${DISEASE_LABELS[pred.disease_type] ?? pred.disease_type} 위험도 변화`,
          body: `${RISK_LABELS[prev] ?? prev}에서 ${RISK_LABELS[pred.risk_level] ?? pred.risk_level}(으)로 변했습니다.`,
        });
        pushed = true;
      }
      nextMap[pred.disease_type] = pred.risk_level;
    }

    localStorage.setItem(riskLevelCacheKey(), JSON.stringify(nextMap));
    // 로컬에서 알림을 직접 push한 경우 riskPoll 커서를 현재 시각으로 앞당겨
    // 30초 이내 폴링이 동일한 RISK_CHANGE 알림을 중복 표시하지 않도록 한다.
    if (pushed) {
      localStorage.setItem(notifRiskPollKey(), new Date().toISOString());
    }
  } catch { /* 무시 */ }
}
