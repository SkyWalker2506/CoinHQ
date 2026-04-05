"use client";

import type { ExchangeBalance } from "@/lib/types";

interface Props {
  exchanges: ExchangeBalance[];
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
}

export default function ExchangeList({ exchanges }: Props) {
  if (exchanges.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex items-center justify-center h-64">
        <p className="text-gray-500 text-sm">No exchange data</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h3 className="text-sm font-medium text-gray-400 mb-4">Exchange Balances</h3>
      <div className="space-y-4">
        {exchanges.map((exchange, idx) => (
          <div key={idx}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-white capitalize">
                {exchange.exchange}
              </span>
              <span className="text-sm text-gray-300">{formatUsd(exchange.total_usd)}</span>
            </div>
            <div className="space-y-1">
              {exchange.balances
                .sort((a, b) => (b.usd_value ?? 0) - (a.usd_value ?? 0))
                .slice(0, 5)
                .map((balance) => (
                  <div
                    key={balance.asset}
                    className="flex items-center justify-between text-xs text-gray-400 pl-2"
                  >
                    <span>{balance.asset}</span>
                    <span className="flex gap-4">
                      <span>{balance.total.toFixed(6)}</span>
                      {balance.usd_value !== undefined && (
                        <span className="text-gray-500">{formatUsd(balance.usd_value)}</span>
                      )}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
