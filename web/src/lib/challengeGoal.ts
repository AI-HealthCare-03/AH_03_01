import type { Challenge, ExerciseSubType } from "@/types/challenge";

const SUB_CATEGORY_LABEL: Record<ExerciseSubType, string> = {
  WALKING: "걷기",
  RUNNING: "러닝",
  STRENGTH: "근력",
  CYCLING: "자전거",
  SWIMMING: "수영",
  OTHER: "기타",
};

const DIET_TYPE_LABEL: Record<string, string> = {
  MEDITERRANEAN: "지중해식",
  LOW_CARB: "저탄수",
  LOW_FAT: "저지방",
  LOW_SODIUM: "저염",
  LOW_SUGAR: "저당",
};

/* goal_type/goal_config 를 사람이 읽을 수 있는 목표 설명으로 변환 */
export function formatGoalDescription(challenge: Challenge): string | null {
  const gc = challenge.goal_config ?? {};
  const parts: string[] = [];

  if (challenge.sub_category) {
    parts.push(SUB_CATEGORY_LABEL[challenge.sub_category] ?? challenge.sub_category);
  }
  if (gc.exercise_other_type) parts.push(gc.exercise_other_type);

  if (gc.diet_type) parts.push(DIET_TYPE_LABEL[gc.diet_type] ?? gc.diet_type);
  if (gc.diet_mode && gc.diet_targets?.length) {
    parts.push(`${gc.diet_mode === "AVOID" ? "피하기" : "먹기"}: ${gc.diet_targets.join(", ")}`);
  }

  if (gc.weight_loss_mode === "USER_INPUT" && gc.weight_loss_kg) {
    parts.push(`체중 ${gc.weight_loss_kg}kg 감량`);
  } else if (gc.weight_loss_mode === "PERCENT_5") {
    parts.push("체중 5% 감량");
  } else if (gc.weight_loss_mode === "MAINTAIN") {
    parts.push("체중 유지");
  }

  if (gc.sleep_time_range) parts.push(`취침 ${gc.sleep_time_range}시`);
  if (gc.sleep_duration_hours) parts.push(`수면 ${gc.sleep_duration_hours}시간`);
  if (gc.wake_time) parts.push(`기상 ${gc.wake_time}`);

  if (gc.amount) parts.push(`${gc.amount.value}${gc.amount.unit}`);
  if (gc.duration_minutes) parts.push(`${gc.duration_minutes}분`);
  if (gc.distance_km) parts.push(`${gc.distance_km}km`);
  if (gc.step_count) parts.push(`${gc.step_count.toLocaleString()}보`);

  if (gc.weekly_target_count) parts.push(`주 ${gc.weekly_target_count}회`);
  if (gc.group_target_count) parts.push(`그룹 합산 ${gc.group_target_count}회`);
  if (gc.group_target_members) parts.push(`${gc.group_target_members}명 달성`);

  return parts.length ? parts.join(" · ") : null;
}
