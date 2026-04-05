"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import type { ExchangeBalance } from "@/lib/types";

const COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

interface Props {
  exchanges: ExchangeBalance[];
}

export default function AllocationChart({ exchanges }: Props) {
  // Build asset allocation data
  const assetMap: Record<string, number> = {};
  for (const exchange of exchanges) {
    for (const balance of exchange.balances) {
      if (balance.usd_value && balance.usd_value > 0) {
        assetMap[balance.asset] = (assetMap[balance.asset] ?? 0) + balance.usd_value;
      }
    }
  }

  const data = Object.entries(assetMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([name, value]) => ({ name, value: parseFloat(value.toFixed(2)) }));

  if (data.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex items-center justify-center h-64">
        <p className="text-gray-500 text-sm">No allocation data</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h3 className="text-sm font-medium text-gray-400 mb-4">Asset Allocation</h3>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
            {data.map((_, index) => (
              <Cell key={index} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number) =>
              new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value)
            }
            contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px" }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
