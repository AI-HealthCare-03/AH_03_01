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
import { useIsDarkMode } from "@/hooks/useIsDarkMode";

interface BPTrendChartProps {
  series: StatSeriesPoint[];
}

export default function BPTrendChart({ series }: BPTrendChartProps) {
  const isDark = useIsDarkMode();
  const data = series.map((p) => ({
    date: format(new Date(p.measured_at), "M/d", { locale: ko }),
    수축기: parseFloat(p.primary_value),
    이완기: p.secondary_value ? parseFloat(p.secondary_value) : undefined,
  }));

  const c = isDark
    ? {
        grid: "#3a3a3a",
        tick: "#b0b0b0",
        dangerBg: "#3a0d0d",
        dangerLabel: "#ef9a9a",
        warningBg: "#332b10",
        warningLabel: "#ffd43b",
        normalBg: "#0d2a14",
        normalLabel: "#81c784",
        systolic: "#ff6b6b",
        diastolic: "#74c0fc",
        tooltipBg: "#242424",
        tooltipBorder: "#3a3a3a",
        tooltipText: "#f0f0f0",
      }
    : {
        grid: "#f0f0f0",
        tick: "#999",
        dangerBg: "#ffeaea",
        dangerLabel: "#e53935",
        warningBg: "#fffbe6",
        warningLabel: "#856404",
        normalBg: "#e8f5e9",
        normalLabel: "#2e7d32",
        systolic: "#DC2626",
        diastolic: "#2563EB",
        tooltipBg: "#fff",
        tooltipBorder: "#e0e0e0",
        tooltipText: "#111",
      };
  const areaOpacity = isDark ? { danger: 0.6, warning: 0.6, normal: 0.5 } : { danger: 0.4, warning: 0.5, normal: 0.3 };

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart
        data={data}
        margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
      >
        {/* 위험 구간 배경 (수축기 기준) */}
        <ReferenceArea y1={140} y2={200} fill={c.dangerBg} fillOpacity={areaOpacity.danger}
          label={{ value: "위험", position: "insideTopRight", fill: c.dangerLabel, fontSize: 10, fontWeight: 600 }} />
        {/* 주의 구간 배경 */}
        <ReferenceArea y1={120} y2={140} fill={c.warningBg} fillOpacity={areaOpacity.warning}
          label={{ value: "주의", position: "insideTopRight", fill: c.warningLabel, fontSize: 10, fontWeight: 600 }} />
        {/* 정상 구간 배경 */}
        <ReferenceArea y1={60} y2={120} fill={c.normalBg} fillOpacity={areaOpacity.normal}
          label={{ value: "정상", position: "insideTopRight", fill: c.normalLabel, fontSize: 10, fontWeight: 600 }} />

        <CartesianGrid strokeDasharray="3 3" stroke={c.grid} />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: c.tick }} />
        <YAxis
          domain={[40, 200]}
          unit="mmHg"
          tick={{ fontSize: 11, fill: c.tick }}
          width={60}
        />
        <Tooltip
          formatter={(value, name) => [`${Number(value)} mmHg`, String(name)]}
          labelStyle={{ color: c.tooltipText }}
          contentStyle={{
            borderRadius: 8,
            border: `1px solid ${c.tooltipBorder}`,
            fontSize: 12,
            backgroundColor: c.tooltipBg,
            color: c.tooltipText,
          }}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, paddingTop: 8, color: c.tick }}
        />

        {/* 기준선 */}
        <ReferenceLine y={120} stroke={c.warningLabel} strokeDasharray="4 2" />
        <ReferenceLine y={140} stroke={c.dangerLabel} strokeDasharray="4 2" />

        <Line
          type="monotone"
          dataKey="수축기"
          stroke={c.systolic}
          strokeWidth={2}
          dot={{ r: 3, fill: c.systolic }}
          activeDot={{ r: 5 }}
          connectNulls
        />
        <Line
          type="monotone"
          dataKey="이완기"
          stroke={c.diastolic}
          strokeWidth={2}
          dot={{ r: 3, fill: c.diastolic }}
          activeDot={{ r: 5 }}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
