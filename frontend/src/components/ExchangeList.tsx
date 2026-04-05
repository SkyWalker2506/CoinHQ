"use client";

import { useState } from "react";
import type { ExchangeBalance } from "@/lib/types";
import { EmptyState } from "./EmptyState";

interface Props {
  exchanges: ExchangeBalance[];
  onAddKey?: () => void;
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(value);
}

function ExchangeItem({ exchange }: { exchange: ExchangeBalance }) {
  const [showAll, setShowAll] = useState(false);
  const sorted = [...exchange.balances].sort(
    (a, b) => (b.usd_value ?? 0) - (a.usd_value ?? 0)
  );
  const displayed = showAll ? sorted : sorted.slice(0, 5);

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-semibold text-white capitalize">
          {exchange.exchange}
        </span>
        <span className="text-sm text-gray-300">{formatUsd(exchange.total_usd)}</span>
      </div>
      <div className="space-y-1">
        {displayed.map((balance) => (
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
      {sorted.length > 5 && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="text-sm text-blue-500 hover:text-blue-400 mt-2"
        >
          {showAll ? "Show less" : `Show all ${sorted.length} assets`}
        </button>
      )}
    </div>
  );
}

export default function ExchangeList({ exchanges, onAddKey }: Props) {
  if (exchanges.length === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <EmptyState
          icon="🔗"
          title="No exchanges connected"
          description="Add your read-only API keys to start tracking your portfolio."
          action={onAddKey ? { label: "Connect exchange", onClick: onAddKey } : undefined}
        />
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h3 className="text-sm font-medium text-gray-400 mb-4">Exchange Balances</h3>
      <div className="space-y-4">
        {exchanges.map((exchange, idx) => (
          <ExchangeItem key={idx} exchange={exchange} />
        ))}
      </div>
    </div>
  );
}
