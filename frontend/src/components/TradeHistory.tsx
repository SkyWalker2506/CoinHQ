"use client";

import type { TradeOrder } from "@/lib/types";
import { useTradeHistory } from "@/hooks/usePortfolio";

// ── Formatting helpers ────────────────────────────────────────────────────────

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SideBadge({ side }: { side: TradeOrder["side"] }) {
  const isBuy = side === "buy";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold uppercase ${
        isBuy ? "bg-green-900/50 text-green-400" : "bg-red-900/50 text-red-400"
      }`}
    >
      {side}
    </span>
  );
}

function StatusBadge({ status, error }: { status: TradeOrder["status"]; error: string | null }) {
  const styles: Record<string, string> = {
    filled: "bg-green-900/50 text-green-400",
    pending: "bg-amber-900/50 text-amber-400",
    failed: "bg-red-900/50 text-red-400",
  };
  const cls = styles[status] ?? "bg-gray-800 text-gray-400";

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-sm text-xs font-semibold capitalize ${cls}`}
      title={status === "failed" && error ? error : undefined}
    >
      {status}
      {status === "failed" && error && (
        <span className="ml-1 text-red-300 text-xs" aria-label={`Error: ${error}`}>
          {" "}({error})
        </span>
      )}
    </span>
  );
}

function ActorBadge({ actor }: { actor: string }) {
  const isOwner = actor === "owner";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${
        isOwner ? "bg-blue-900/50 text-blue-300" : "bg-purple-900/50 text-purple-300"
      }`}
    >
      {actor}
    </span>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface TradeHistoryProps {
  profileId: number | null;
}

export default function TradeHistory({ profileId }: TradeHistoryProps) {
  const { trades, error, isLoading } = useTradeHistory(profileId);

  if (profileId == null) {
    return (
      <div
        role="status"
        className="mt-4 p-4 bg-gray-800/50 rounded-lg text-gray-400 text-sm text-center"
      >
        Select a profile to view trade history.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div
        role="status"
        aria-live="polite"
        aria-label="Loading trade history"
        className="mt-4 space-y-2"
      >
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-12 bg-gray-800 rounded-sm animate-pulse" />
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
        Failed to load trade history: {error.message ?? String(error)}
      </div>
    );
  }

  if (!trades || trades.length === 0) {
    return (
      <div
        role="status"
        className="mt-4 p-8 text-center text-gray-500 text-sm bg-gray-800/30 rounded-lg"
      >
        No trades yet.
      </div>
    );
  }

  return (
    <div className="mt-4 overflow-x-auto rounded-lg border border-gray-700">
      <table className="min-w-full divide-y divide-gray-700 text-sm">
        <thead className="bg-gray-800/60">
          <tr>
            {["Date", "Side", "Asset", "Exchange", "Amount", "USD Value", "Actor", "Status"].map(
              (h) => (
                <th
                  key={h}
                  scope="col"
                  className="px-4 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider"
                >
                  {h}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700/50">
          {trades.map((t) => (
            <tr
              key={t.id}
              className={`transition-colors hover:bg-gray-800/40 ${
                t.status === "failed" ? "bg-red-950/20" : ""
              }`}
            >
              <td className="px-4 py-3 text-gray-300 whitespace-nowrap">{formatDate(t.created_at)}</td>
              <td className="px-4 py-3">
                <SideBadge side={t.side} />
              </td>
              <td className="px-4 py-3 font-medium text-white">{t.base_asset}</td>
              <td className="px-4 py-3 text-gray-300 capitalize">{t.exchange}</td>
              <td className="px-4 py-3 text-gray-300">
                {t.amount != null ? t.amount.toFixed(6) : "—"}
              </td>
              <td className="px-4 py-3 text-gray-100 font-medium">{formatUsd(t.usd_value)}</td>
              <td className="px-4 py-3">
                <ActorBadge actor={t.actor} />
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={t.status} error={t.error} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
