"use client";

import { useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { usePortfolioHistory } from "@/hooks/usePortfolio";
import type { PortfolioSnapshot } from "@/lib/types";

// ── Formatting helpers ────────────────────────────────────────────────────────

function formatShortDate(iso: string): string {
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(
    new Date(iso)
  );
}

function formatFullDate(iso: string): string {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

function formatCompactUsd(value: number): string {
  if (value >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `$${(value / 1_000).toFixed(1)}k`;
  }
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(value);
}

function formatFullUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

// ── Custom Tooltip ────────────────────────────────────────────────────────────

interface TooltipPayloadItem {
  value: number;
  payload: { created_at: string; total_usd: number };
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const item = payload[0];
  return (
    <div
      style={{
        backgroundColor: "#111827",
        border: "1px solid #374151",
        borderRadius: "8px",
        padding: "8px 12px",
        fontSize: "13px",
      }}
    >
      <p className="text-gray-400 text-xs">{formatFullDate(item.payload.created_at)}</p>
      <p className="text-white font-semibold mt-0.5">{formatFullUsd(item.value)}</p>
    </div>
  );
}

// ── Range Toggle ──────────────────────────────────────────────────────────────

const RANGES: { label: string; days: number }[] = [
  { label: "7D", days: 7 },
  { label: "30D", days: 30 },
  { label: "90D", days: 90 },
];

// ── Main component ────────────────────────────────────────────────────────────

interface PortfolioHistoryChartProps {
  profileId: number | null;
}

export default function PortfolioHistoryChart({ profileId }: PortfolioHistoryChartProps) {
  const [days, setDays] = useState<number>(30);
  const { history, error, isLoading } = usePortfolioHistory(profileId, days);

  if (profileId == null) {
    return (
      <div
        role="status"
        className="bg-gray-900 border border-gray-800 rounded-xl p-6 text-gray-400 text-sm text-center"
      >
        Select a profile to view portfolio history.
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
          Portfolio Value History
        </h3>
        <div className="flex gap-1" role="group" aria-label="Date range">
          {RANGES.map(({ label, days: d }) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              aria-pressed={days === d}
              className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                days === d
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* States */}
      {isLoading && (
        <div
          role="status"
          aria-live="polite"
          aria-label="Loading portfolio history"
          className="h-48 flex items-center justify-center"
        >
          <div className="h-48 w-full bg-gray-800 rounded-sm animate-pulse" />
        </div>
      )}

      {error && !isLoading && (
        <div
          role="alert"
          className="h-48 flex items-center justify-center text-red-300 text-sm"
        >
          Failed to load portfolio history: {(error as Error).message ?? String(error)}
        </div>
      )}

      {!isLoading && !error && history && history.length < 2 && (
        <div
          role="status"
          className="h-48 flex items-center justify-center text-gray-500 text-sm text-center px-4"
        >
          Not enough history yet — value is recorded as you use the app.
        </div>
      )}

      {!isLoading && !error && history && history.length >= 2 && (
        <div role="img" aria-label="Portfolio value over time area chart">
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={history as PortfolioSnapshot[]}>
              <defs>
                <linearGradient id="histGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
              <XAxis
                dataKey="created_at"
                tickFormatter={formatShortDate}
                tick={{ fontSize: 11, fill: "#6b7280" }}
                axisLine={false}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                tickFormatter={formatCompactUsd}
                tick={{ fontSize: 11, fill: "#6b7280" }}
                axisLine={false}
                tickLine={false}
                width={60}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="total_usd"
                stroke="#3b82f6"
                strokeWidth={2}
                fill="url(#histGradient)"
                dot={false}
                activeDot={{ r: 4, fill: "#3b82f6" }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
