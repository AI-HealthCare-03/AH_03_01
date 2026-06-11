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
  ReferenceArea,
  Legend,
} from "recharts";
import { format } from "date-fns";
import { ko } from "date-fns/locale";
import type { StatSeriesPoint } from "@/types/health";

interface BPTrendChartProps {
  series: StatSeriesPoint[];
}

export default function BPTrendChart({ series }: BPTrendChartProps) {
  const data = series.map((p) => ({
    date: format(new Date(p.measured_at), "M/d", { locale: ko }),
    수축기: parseFloat(p.primary_value),
    이완기: p.secondary_value ? parseFloat(p.secondary_value) : undefined,
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart
        data={data}
        margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
      >
        {/* 위험 구간 배경 (수축기 기준) */}
        <ReferenceArea y1={140} y2={200} fill="#ffeaea" fillOpacity={0.4}
          label={{ value: "위험", position: "insideTopRight", fill: "#e53935", fontSize: 10, fontWeight: 600 }} />
        {/* 주의 구간 배경 */}
        <ReferenceArea y1={120} y2={140} fill="#fffbe6" fillOpacity={0.5}
          label={{ value: "주의", position: "insideTopRight", fill: "#856404", fontSize: 10, fontWeight: 600 }} />
        {/* 정상 구간 배경 */}
        <ReferenceArea y1={60} y2={120} fill="#e8f5e9" fillOpacity={0.3}
          label={{ value: "정상", position: "insideTopRight", fill: "#2e7d32", fontSize: 10, fontWeight: 600 }} />

        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#999" }} />
        <YAxis
          domain={[40, 200]}
          unit="mmHg"
          tick={{ fontSize: 11, fill: "#999" }}
          width={60}
        />
        <Tooltip
          formatter={(value, name) => [`${Number(value)} mmHg`, String(name)]}
          labelStyle={{ color: "#111" }}
          contentStyle={{
            borderRadius: 8,
            border: "1px solid #e0e0e0",
            fontSize: 12,
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
        />

        {/* 기준선 */}
        <ReferenceLine y={120} stroke="#f9a825" strokeDasharray="4 2" />
        <ReferenceLine y={140} stroke="#e53935" strokeDasharray="4 2" />

        <Line
          type="monotone"
          dataKey="수축기"
          stroke="#DC2626"
          strokeWidth={2}
          dot={{ r: 3, fill: "#DC2626" }}
          activeDot={{ r: 5 }}
          connectNulls
        />
        <Line
          type="monotone"
          dataKey="이완기"
          stroke="#2563EB"
          strokeWidth={2}
          dot={{ r: 3, fill: "#2563EB" }}
          activeDot={{ r: 5 }}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
