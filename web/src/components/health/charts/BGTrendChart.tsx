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
import { useIsDarkMode } from "@/hooks/useIsDarkMode";

interface BGTrendChartProps {
  series: StatSeriesPoint[];
}

export default function BGTrendChart({ series }: BGTrendChartProps) {
  const isDark = useIsDarkMode();
  const data = series.map((p) => ({
    date: format(new Date(p.measured_at), "M/d", { locale: ko }),
    공복혈당: parseFloat(p.primary_value),
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
        line: "#74c0fc",
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
        line: "#2563EB",
        tooltipBg: "#fff",
        tooltipBorder: "#e0e0e0",
        tooltipText: "#111",
      };
  const areaOpacity = isDark ? { danger: 0.6, warning: 0.6, normal: 0.5 } : { danger: 0.4, warning: 0.5, normal: 0.3 };

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart
        data={data}
        /* right 여백 확대: 기준선 라벨(position="right")이 오른쪽 끝에서 잘리지 않도록. */
        margin={{ top: 8, right: 64, left: 0, bottom: 0 }}
      >
        {/* 구간 배경 */}
        <ReferenceArea y1={140} y2={250} fill={c.dangerBg} fillOpacity={areaOpacity.danger}
          label={{ value: "위험", position: "insideTopRight", fill: c.dangerLabel, fontSize: 10, fontWeight: 600 }} />
        <ReferenceArea y1={100} y2={140} fill={c.warningBg} fillOpacity={areaOpacity.warning}
          label={{ value: "주의", position: "insideTopRight", fill: c.warningLabel, fontSize: 10, fontWeight: 600 }} />
        <ReferenceArea y1={60} y2={100} fill={c.normalBg} fillOpacity={areaOpacity.normal}
          label={{ value: "정상", position: "insideTopRight", fill: c.normalLabel, fontSize: 10, fontWeight: 600 }} />

        <CartesianGrid strokeDasharray="3 3" stroke={c.grid} />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: c.tick }} />
        <YAxis
          domain={[60, 250]}
          unit="mg/dL"
          tick={{ fontSize: 11, fill: c.tick }}
          width={70}
        />
        <Tooltip
          formatter={(value) => [`${Number(value)} mg/dL`, "공복혈당"]}
          contentStyle={{
            borderRadius: 8,
            border: `1px solid ${c.tooltipBorder}`,
            fontSize: 12,
            backgroundColor: c.tooltipBg,
            color: c.tooltipText,
          }}
        />

        {/* 공복 기준선 */}
        <ReferenceLine
          y={100}
          stroke={c.warningLabel}
          strokeDasharray="4 2"
          label={{ value: "정상상한 100", position: "right", fontSize: 10, fill: c.warningLabel }}
        />
        <ReferenceLine
          y={126}
          stroke={c.dangerLabel}
          strokeDasharray="4 2"
          label={{ value: "당뇨기준 126", position: "right", fontSize: 10, fill: c.dangerLabel }}
        />

        <Line
          type="monotone"
          dataKey="공복혈당"
          stroke={c.line}
          strokeWidth={2}
          dot={{ r: 3, fill: c.line }}
          activeDot={{ r: 5 }}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
