"use client";

import type { PnlAsset } from "@/lib/types";
import { useProfilePnl } from "@/hooks/usePortfolio";

// ── Formatting helpers ────────────────────────────────────────────────────────

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatQty(value: number): string {
  return value.toLocaleString("en-US", { maximumFractionDigits: 6 });
}

// ── Sub-components ────────────────────────────────────────────────────────────

function PnlValue({ value }: { value: number }) {
  const positive = value >= 0;
  return (
    <span className={positive ? "text-green-400 font-medium" : "text-red-400 font-medium"}>
      {positive ? "+" : ""}
      {formatUsd(value)}
    </span>
  );
}

function AssetRow({ asset }: { asset: PnlAsset }) {
  return (
    <tr className="transition-colors hover:bg-gray-800/40">
      <td className="px-4 py-3 font-medium text-white">{asset.base_asset}</td>
      <td className="px-4 py-3 text-gray-300">{formatQty(asset.current_qty)}</td>
      <td className="px-4 py-3 text-gray-300">
        {asset.avg_cost != null ? formatUsd(asset.avg_cost) : "—"}
      </td>
      <td className="px-4 py-3">
        <PnlValue value={asset.realized_pnl_usd} />
      </td>
      <td className="px-4 py-3 text-gray-400 text-sm">
        {asset.buy_count}B / {asset.sell_count}S
      </td>
    </tr>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface RealizedPnLProps {
  profileId: number | null;
}

export default function RealizedPnL({ profileId }: RealizedPnLProps) {
  const { pnl, error, isLoading } = useProfilePnl(profileId);

  if (profileId == null) {
    return (
      <div
        role="status"
        className="mt-4 p-4 bg-gray-800/50 rounded-lg text-gray-400 text-sm text-center"
      >
        Select a profile to view realized P&amp;L.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div
        role="status"
        aria-live="polite"
        aria-label="Loading realized P&L"
        className="mt-4 space-y-2"
      >
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-10 bg-gray-800 rounded animate-pulse" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        className="mt-4 p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm"
      >
        Failed to load realized P&amp;L: {(error as Error).message ?? String(error)}
      </div>
    );
  }

  if (!pnl || pnl.assets.length === 0) {
    return (
      <div
        role="status"
        className="mt-4 p-8 text-center text-gray-500 text-sm bg-gray-800/30 rounded-lg"
      >
        No completed trades yet.
      </div>
    );
  }

  const total = pnl.total_realized_pnl_usd;
  const positive = total >= 0;

  return (
    <div className="mt-4">
      {/* Header: total realized P&L */}
      <div className="flex items-baseline gap-3 mb-1">
        <span
          className={`text-2xl font-bold tabular-nums ${
            positive ? "text-green-400" : "text-red-400"
          }`}
          aria-label={`Total realized P&L: ${formatUsd(total)}`}
        >
          {positive ? "+" : ""}
          {formatUsd(total)}
        </span>
      </div>
      <p className="text-xs text-gray-500 mb-4">
        Realized P&amp;L &middot; CoinHQ trades only (excludes positions traded directly on
        exchanges)
      </p>

      {/* Per-asset table */}
      <div className="overflow-x-auto rounded-lg border border-gray-700">
        <table className="min-w-full divide-y divide-gray-700 text-sm">
          <thead className="bg-gray-800/60">
            <tr>
              {["Asset", "Qty (CoinHQ)", "Avg Cost", "Realized P&L", "Trades"].map((h) => (
                <th
                  key={h}
                  scope="col"
                  className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700/50">
            {pnl.assets.map((asset) => (
              <AssetRow key={asset.base_asset} asset={asset} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
