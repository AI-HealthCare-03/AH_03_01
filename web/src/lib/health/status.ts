/* =========================================
   건강 지표 상태 등급 판정 헬퍼
   BMI / 혈압 / 공복혈당 / HbA1c
   ========================================= */

export type HealthStatus = "정상" | "주의" | "위험";

/** 상태 → Tailwind 클래스 매핑 */
export const statusColorClass: Record<
  HealthStatus,
  { bg: string; text: string; border: string }
> = {
  정상: {
    bg: "bg-[#e8f5e9]",
    text: "text-[#2e7d32]",
    border: "border-[#2e7d32]",
  },
  주의: {
    bg: "bg-[#fffbe6]",
    text: "text-[#856404]",
    border: "border-[#f9e000]",
  },
  위험: {
    bg: "bg-[#ffeaea]",
    text: "text-[#e53935]",
    border: "border-[#e53935]",
  },
};

/** BMI 상태 판정 */
export function getBmiStatus(bmi: number): HealthStatus {
  if (bmi < 18.5 || bmi >= 25) return "위험";
  if (bmi >= 23) return "주의";
  return "정상";
}

/** BMI 계산 (height_cm, weight_kg → 소수점 1자리) */
export function calcBmi(heightCm: number, weightKg: number): number {
  const h = heightCm / 100;
  return Math.round((weightKg / (h * h)) * 10) / 10;
}

/** 혈압 상태 판정 (수축기 기준) */
export function getBloodPressureStatus(systolic: number): HealthStatus {
  if (systolic >= 140) return "위험";
  if (systolic >= 120) return "주의";
  return "정상";
}

/** 공복혈당 상태 판정 */
export function getFastingGlucoseStatus(value: number): HealthStatus {
  if (value >= 126) return "위험";
  if (value >= 100) return "주의";
  return "정상";
}

/** HbA1c 상태 판정 */
export function getHba1cStatus(value: number): HealthStatus {
  if (value >= 6.5) return "위험";
  if (value >= 5.7) return "주의";
  return "정상";
}
