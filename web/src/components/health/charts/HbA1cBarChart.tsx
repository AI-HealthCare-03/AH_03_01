"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Cell,
} from "recharts";
import { format } from "date-fns";
import { ko } from "date-fns/locale";
import { getHba1cStatus } from "@/lib/health/status";
import type { StatSeriesPoint } from "@/types/health";

interface HbA1cBarChartProps {
  series: StatSeriesPoint[];
}

const STATUS_COLOR: Record<string, string> = {
  정상: "#2e7d32",
  주의: "#f9a825",
  위험: "#e53935",
};

export default function HbA1cBarChart({ series }: HbA1cBarChartProps) {
  /* 최근 4회만 */
  const data = series.slice(-4).map((p) => {
    const value = parseFloat(p.primary_value);
    const status = getHba1cStatus(value);
    return {
      date: format(new Date(p.measured_at), "M/d", { locale: ko }),
      HbA1c: value,
      color: STATUS_COLOR[status],
    };
  });

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#999" }} />
        <YAxis
          domain={[4, 12]}
          unit="%"
          tick={{ fontSize: 11, fill: "#999" }}
          width={45}
        />
        <Tooltip
          formatter={(value) => [`${Number(value)}%`, "HbA1c"]}
          contentStyle={{ borderRadius: 8, border: "1px solid #e0e0e0", fontSize: 12 }}
        />
        {/* 기준선 */}
        <ReferenceLine y={5.7} stroke="#f9a825" strokeDasharray="4 2" />
        <ReferenceLine y={6.5} stroke="#e53935" strokeDasharray="4 2" />

        <Bar dataKey="HbA1c" radius={[6, 6, 0, 0]}>
          {data.map((entry, index) => (
            <Cell key={index} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
