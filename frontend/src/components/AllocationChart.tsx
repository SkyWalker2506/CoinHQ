"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import type { ExchangeBalance } from "@/lib/types";

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16"];

interface Props {
  exchanges: ExchangeBalance[];
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 }).format(value);
}

export default function AllocationChart({ exchanges }: Props) {
  const assetMap: Record<string, number> = {};
  for (const exchange of exchanges) {
    for (const balance of exchange.balances) {
      if (balance.usd_value && balance.usd_value > 0) {
        assetMap[balance.asset] = (assetMap[balance.asset] ?? 0) + balance.usd_value;
      }
    }
  }

  const total = Object.values(assetMap).reduce((acc, v) => acc + v, 0);
  const sorted = Object.entries(assetMap).sort((a, b) => b[1] - a[1]);
  const top = sorted.slice(0, 8);
  const othersValue = sorted.slice(8).reduce((acc, [, v]) => acc + v, 0);

  const data = [
    ...top.map(([name, value]) => ({
      name,
      value: parseFloat(value.toFixed(2)),
      percentage: total > 0 ? parseFloat(((value / total) * 100).toFixed(1)) : 0,
    })),
    ...(othersValue > 0 ? [{ name: "Others", value: parseFloat(othersValue.toFixed(2)), percentage: parseFloat(((othersValue / total) * 100).toFixed(1)) }] : []),
  ];

  if (data.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex items-center justify-center h-64">
        <p className="text-gray-500 text-sm">No allocation data</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">Asset Allocation</h3>

      <div role="img" aria-label="Asset allocation pie chart">
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={85}
              paddingAngle={2}
            >
              {data.map((_, index) => (
                <Cell key={index} fill={COLORS[index % COLORS.length]} stroke="transparent" />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => [formatUsd(value), "Value"]}
              contentStyle={{ backgroundColor: "#111827", border: "1px solid #374151", borderRadius: "8px", fontSize: "13px" }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Legend table */}
      <div className="mt-3 space-y-1.5">
        {data.map((item, index) => (
          <div key={item.name} className="flex items-center gap-2.5">
            <span
              className="w-2.5 h-2.5 rounded-full shrink-0"
              style={{ backgroundColor: COLORS[index % COLORS.length] }}
            />
            <span className="text-sm text-gray-300 flex-1 truncate font-medium">{item.name}</span>
            <span className="text-xs text-gray-500 w-10 text-right">{item.percentage}%</span>
            <span className="text-sm text-white w-24 text-right tabular-nums">{formatUsd(item.value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
