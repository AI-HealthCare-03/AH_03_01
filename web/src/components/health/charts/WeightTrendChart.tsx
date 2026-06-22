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
  ReferenceArea,
} from "recharts";
import { format } from "date-fns";
import { ko } from "date-fns/locale";
import { calcBmi } from "@/lib/health/status";
import type { StatSeriesPoint } from "@/types/health";
import { useIsDarkMode } from "@/hooks/useIsDarkMode";

interface WeightTrendChartProps {
  series: StatSeriesPoint[];
  heightCm?: number;
}

export default function WeightTrendChart({ series, heightCm }: WeightTrendChartProps) {
  const isDark = useIsDarkMode();
  const data = series.map((p) => {
    const weight = parseFloat(p.primary_value);
    return {
      date: format(new Date(p.measured_at), "M/d", { locale: ko }),
      체중: weight,
      BMI: heightCm ? calcBmi(heightCm, weight) : undefined,
    };
  });

  const c = isDark
    ? {
        grid: "#3a3a3a",
        tick: "#b0b0b0",
        obeseBg: "#3a0d0d",
        obeseLabel: "#ef9a9a",
        overweightBg: "#332b10",
        overweightLabel: "#ffd43b",
        normalBg: "#0d2a14",
        normalLabel: "#81c784",
        weightLine: "#74c0fc",
        bmiLine: "#ffd43b",
        tooltipBg: "#242424",
        tooltipBorder: "#3a3a3a",
        tooltipText: "#f0f0f0",
      }
    : {
        grid: "#f0f0f0",
        tick: "#999",
        obeseBg: "#ffeaea",
        obeseLabel: "#e53935",
        overweightBg: "#fffbe6",
        overweightLabel: "#856404",
        normalBg: "#e8f5e9",
        normalLabel: "#2e7d32",
        weightLine: "#2563EB",
        bmiLine: "#f9a825",
        tooltipBg: "#fff",
        tooltipBorder: "#e0e0e0",
        tooltipText: "#111",
      };
  const areaOpacity = isDark
    ? { obese: 0.55, overweight: 0.55, normal: 0.45 }
    : { obese: 0.3, overweight: 0.4, normal: 0.25 };

  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        {/* BMI 구간 배경 (BMI 우측 축 기준, heightCm 있을 때만) */}
        {heightCm && (
          <>
            <ReferenceArea yAxisId="bmi" y1={25} y2={40} fill={c.obeseBg} fillOpacity={areaOpacity.obese}
              label={{ value: "비만", position: "insideTopRight", fill: c.obeseLabel, fontSize: 10, fontWeight: 600 }} />
            <ReferenceArea yAxisId="bmi" y1={23} y2={25} fill={c.overweightBg} fillOpacity={areaOpacity.overweight}
              label={{ value: "과체중", position: "insideTopRight", fill: c.overweightLabel, fontSize: 10, fontWeight: 600 }} />
            <ReferenceArea yAxisId="bmi" y1={10} y2={23} fill={c.normalBg} fillOpacity={areaOpacity.normal}
              label={{ value: "정상", position: "insideTopRight", fill: c.normalLabel, fontSize: 10, fontWeight: 600 }} />
          </>
        )}

        <CartesianGrid strokeDasharray="3 3" stroke={c.grid} />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: c.tick }} />
        {/* 좌측 Y축: 체중 */}
        <YAxis
          yAxisId="weight"
          unit="kg"
          tick={{ fontSize: 11, fill: c.tick }}
          width={55}
        />
        {/* 우측 Y축: BMI */}
        {heightCm && (
          <YAxis
            yAxisId="bmi"
            orientation="right"
            domain={[10, 40]}
            tick={{ fontSize: 11, fill: c.tick }}
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
          contentStyle={{
            borderRadius: 8,
            border: `1px solid ${c.tooltipBorder}`,
            fontSize: 12,
            backgroundColor: c.tooltipBg,
            color: c.tooltipText,
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8, color: c.tick }} />

        <Line
          yAxisId="weight"
          type="monotone"
          dataKey="체중"
          stroke={c.weightLine}
          strokeWidth={2}
          dot={{ r: 3, fill: c.weightLine }}
          connectNulls
        />
        {heightCm && (
          <Line
            yAxisId="bmi"
            type="monotone"
            dataKey="BMI"
            stroke={c.bmiLine}
            strokeWidth={2}
            strokeDasharray="5 3"
            dot={{ r: 3, fill: c.bmiLine }}
            connectNulls
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
