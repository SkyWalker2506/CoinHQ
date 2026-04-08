"use client";

import { useEffect, useState } from "react";
import { getGlobalMetrics } from "@/lib/api";
import type { GlobalMetrics } from "@/lib/types";

function fmtB(val: number | null): string {
  if (val == null) return "—";
  if (val >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
  if (val >= 1e9) return `$${(val / 1e9).toFixed(1)}B`;
  return `$${(val / 1e6).toFixed(0)}M`;
}

function fmtPct(val: number | null): string {
  if (val == null) return "—";
  return `${val >= 0 ? "+" : ""}${val.toFixed(2)}%`;
}

export function GlobalMarketBar() {
  const [data, setData] = useState<GlobalMetrics | null>(null);

  useEffect(() => {
    getGlobalMetrics()
      .then(setData)
      .catch(() => {});

    const interval = setInterval(() => {
      getGlobalMetrics().then(setData).catch(() => {});
    }, 5 * 60 * 1000); // refresh every 5 min

    return () => clearInterval(interval);
  }, []);

  if (!data) return null;

  const changeColor =
    data.total_market_cap_change_24h != null && data.total_market_cap_change_24h >= 0
      ? "text-green-400"
      : "text-red-400";

  return (
    <div className="bg-gray-900/50 border-b border-gray-800 px-4 py-2">
      <div className="max-w-6xl mx-auto flex items-center gap-4 sm:gap-6 text-xs text-gray-400 overflow-x-auto">
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-gray-500">Market Cap:</span>
          <span className="text-white font-medium">{fmtB(data.total_market_cap)}</span>
          <span className={changeColor}>
            {fmtPct(data.total_market_cap_change_24h)}
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-gray-500">24h Vol:</span>
          <span className="text-white font-medium">{fmtB(data.total_volume_24h)}</span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-gray-500">BTC:</span>
          <span className="text-orange-400 font-medium">
            {data.btc_dominance != null ? `${data.btc_dominance.toFixed(1)}%` : "—"}
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-gray-500">ETH:</span>
          <span className="text-blue-400 font-medium">
            {data.eth_dominance != null ? `${data.eth_dominance.toFixed(1)}%` : "—"}
          </span>
        </div>
        {data.active_cryptocurrencies && (
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="text-gray-500">Coins:</span>
            <span className="text-white">{data.active_cryptocurrencies.toLocaleString()}</span>
          </div>
        )}
      </div>
    </div>
  );
}
