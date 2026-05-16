"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Legend,
} from "recharts";
import { format } from "date-fns";
import { ko } from "date-fns/locale";
import type { StatSeriesPoint } from "@/types/health";

interface BGTrendChartProps {
  fastingSeries: StatSeriesPoint[];
  postmealSeries?: StatSeriesPoint[];
}

export default function BGTrendChart({ fastingSeries, postmealSeries }: BGTrendChartProps) {
  /* 날짜 기준으로 병합 */
  const dateMap: Record<string, { date: string; 공복혈당?: number; 식후혈당?: number }> = {};

  fastingSeries.forEach((p) => {
    const key = format(new Date(p.measured_at), "M/d", { locale: ko });
    dateMap[key] = { ...dateMap[key], date: key, 공복혈당: parseFloat(p.primary_value) };
  });

  postmealSeries?.forEach((p) => {
    const key = format(new Date(p.measured_at), "M/d", { locale: ko });
    dateMap[key] = { ...dateMap[key], date: key, 식후혈당: parseFloat(p.primary_value) };
  });

  const data = Object.values(dateMap).sort((a, b) => a.date.localeCompare(b.date));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart
        data={data}
        margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#999" }} />
        <YAxis
          domain={[60, 250]}
          unit="mg/dL"
          tick={{ fontSize: 11, fill: "#999" }}
          width={70}
        />
        <Tooltip
          formatter={(value, name) => [`${Number(value)} mg/dL`, String(name)]}
          contentStyle={{ borderRadius: 8, border: "1px solid #e0e0e0", fontSize: 12 }}
        />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />

        {/* 공복 기준선 */}
        <ReferenceLine
          y={100}
          stroke="#f9a825"
          strokeDasharray="4 2"
          label={{ value: "공복 정상 상한", position: "right", fontSize: 10, fill: "#856404" }}
        />
        {/* 식후 기준선 */}
        <ReferenceLine
          y={140}
          stroke="#e53935"
          strokeDasharray="4 2"
          label={{ value: "식후 정상 상한", position: "right", fontSize: 10, fill: "#e53935" }}
        />

        <Line
          type="monotone"
          dataKey="공복혈당"
          stroke="#2563EB"
          strokeWidth={2}
          dot={{ r: 3, fill: "#2563EB" }}
          activeDot={{ r: 5 }}
          connectNulls
        />
        <Line
          type="monotone"
          dataKey="식후혈당"
          stroke="#9333ea"
          strokeWidth={2}
          strokeDasharray="5 3"
          dot={{ r: 3, fill: "#9333ea" }}
          activeDot={{ r: 5 }}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
