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
} from "recharts";
import { format } from "date-fns";
import { ko } from "date-fns/locale";
import type { StatSeriesPoint } from "@/types/health";

interface BGTrendChartProps {
  series: StatSeriesPoint[];
}

export default function BGTrendChart({ series }: BGTrendChartProps) {
  const data = series.map((p) => ({
    date: format(new Date(p.measured_at), "M/d", { locale: ko }),
    공복혈당: parseFloat(p.primary_value),
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart
        data={data}
        /* right 여백 확대: 기준선 라벨(position="right")이 오른쪽 끝에서 잘리지 않도록. */
        margin={{ top: 8, right: 64, left: 0, bottom: 0 }}
      >
        {/* 구간 배경 */}
        <ReferenceArea y1={140} y2={250} fill="#ffeaea" fillOpacity={0.4}
          label={{ value: "위험", position: "insideTopRight", fill: "#e53935", fontSize: 10, fontWeight: 600 }} />
        <ReferenceArea y1={100} y2={140} fill="#fffbe6" fillOpacity={0.5}
          label={{ value: "주의", position: "insideTopRight", fill: "#856404", fontSize: 10, fontWeight: 600 }} />
        <ReferenceArea y1={60} y2={100} fill="#e8f5e9" fillOpacity={0.3}
          label={{ value: "정상", position: "insideTopRight", fill: "#2e7d32", fontSize: 10, fontWeight: 600 }} />

        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#999" }} />
        <YAxis
          domain={[60, 250]}
          unit="mg/dL"
          tick={{ fontSize: 11, fill: "#999" }}
          width={70}
        />
        <Tooltip
          formatter={(value) => [`${Number(value)} mg/dL`, "공복혈당"]}
          contentStyle={{ borderRadius: 8, border: "1px solid #e0e0e0", fontSize: 12 }}
        />

        {/* 공복 기준선 */}
        <ReferenceLine
          y={100}
          stroke="#f9a825"
          strokeDasharray="4 2"
          label={{ value: "정상상한 100", position: "right", fontSize: 10, fill: "#856404" }}
        />
        <ReferenceLine
          y={126}
          stroke="#e53935"
          strokeDasharray="4 2"
          label={{ value: "당뇨기준 126", position: "right", fontSize: 10, fill: "#e53935" }}
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
      </LineChart>
    </ResponsiveContainer>
  );
}
