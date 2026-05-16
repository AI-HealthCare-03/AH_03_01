"use client";

import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { format } from "date-fns";
import { ko } from "date-fns/locale";
import { calcBmi } from "@/lib/health/status";
import type { StatSeriesPoint } from "@/types/health";

interface WeightTrendChartProps {
  series: StatSeriesPoint[];
  heightCm?: number;
}

export default function WeightTrendChart({ series, heightCm }: WeightTrendChartProps) {
  const data = series.map((p) => {
    const weight = parseFloat(p.primary_value);
    return {
      date: format(new Date(p.measured_at), "M/d", { locale: ko }),
      체중: weight,
      BMI: heightCm ? calcBmi(heightCm, weight) : undefined,
    };
  });

  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#999" }} />
        {/* 좌측 Y축: 체중 */}
        <YAxis
          yAxisId="weight"
          unit="kg"
          tick={{ fontSize: 11, fill: "#999" }}
          width={55}
        />
        {/* 우측 Y축: BMI */}
        {heightCm && (
          <YAxis
            yAxisId="bmi"
            orientation="right"
            domain={[10, 40]}
            tick={{ fontSize: 11, fill: "#999" }}
            width={40}
            unit=""
          />
        )}
        <Tooltip
          formatter={(value, name) => {
            const n = Number(value);
            if (name === "BMI") return [n.toFixed(1), "BMI"];
            return [`${n} kg`, String(name)];
          }}
          contentStyle={{ borderRadius: 8, border: "1px solid #e0e0e0", fontSize: 12 }}
        />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />

        <Line
          yAxisId="weight"
          type="monotone"
          dataKey="체중"
          stroke="#2563EB"
          strokeWidth={2}
          dot={{ r: 3, fill: "#2563EB" }}
          connectNulls
        />
        {heightCm && (
          <Line
            yAxisId="bmi"
            type="monotone"
            dataKey="BMI"
            stroke="#f9a825"
            strokeWidth={2}
            strokeDasharray="5 3"
            dot={{ r: 3, fill: "#f9a825" }}
            connectNulls
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
