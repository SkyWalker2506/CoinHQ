"use client";

import { useState } from "react";
import { createShareLink } from "@/lib/api";
import type { ShareLink } from "@/lib/types";

interface Props {
  profileId: number;
  onClose: () => void;
  onCreated: (link: ShareLink) => void;
}

const DURATION_OPTIONS = [
  { label: "Unlimited", value: null },
  { label: "1 day", value: 1 },
  { label: "7 days", value: 7 },
  { label: "30 days", value: 30 },
];

export default function CreateShareLinkModal({ profileId, onClose, onCreated }: Props) {
  const [showTotalValue, setShowTotalValue] = useState(true);
  const [showCoinAmounts, setShowCoinAmounts] = useState(false);
  const [showExchangeNames, setShowExchangeNames] = useState(false);
  const [showAllocationPct, setShowAllocationPct] = useState(true);
  const [durationDays, setDurationDays] = useState<number | null>(null);
  const [label, setLabel] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    setLoading(true);
    setError(null);
    try {
      let expiresAt: string | null = null;
      if (durationDays !== null) {
        const d = new Date();
        d.setDate(d.getDate() + durationDays);
        expiresAt = d.toISOString();
      }
      const link = await createShareLink({
        profile_id: profileId,
        show_total_value: showTotalValue,
        show_coin_amounts: showCoinAmounts,
        show_exchange_names: showExchangeNames,
        show_allocation_pct: showAllocationPct,
        expires_at: expiresAt,
        label: label.trim() || null,
      });
      onCreated(link);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create link");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 w-full max-w-md shadow-xl">
        <h2 className="text-lg font-semibold text-white mb-5">Create Share Link</h2>

        {/* Permissions */}
        <div className="space-y-3 mb-5">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wider">Permissions</p>
          {[
            { label: "Show total value", value: showTotalValue, set: setShowTotalValue },
            { label: "Show coin amounts", value: showCoinAmounts, set: setShowCoinAmounts },
            { label: "Show exchange names", value: showExchangeNames, set: setShowExchangeNames },
            { label: "Show allocation %", value: showAllocationPct, set: setShowAllocationPct },
          ].map(({ label, value, set }) => (
            <label key={label} className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                className="w-4 h-4 accent-blue-500"
                checked={value}
                onChange={(e) => set(e.target.checked)}
              />
              <span className="text-sm text-gray-300">{label}</span>
            </label>
          ))}
        </div>

        {/* Duration */}
        <div className="mb-5">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
            Expiry
          </p>
          <div className="flex flex-wrap gap-2">
            {DURATION_OPTIONS.map((opt) => (
              <button
                key={opt.label}
                onClick={() => setDurationDays(opt.value)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  durationDays === opt.value
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 text-gray-300 hover:bg-gray-700"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Label */}
        <div className="mb-6">
          <label className="text-xs font-medium text-gray-400 uppercase tracking-wider block mb-1">
            Label (optional)
          </label>
          <input
            type="text"
            placeholder="e.g. For accountant"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            maxLength={100}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
        </div>

        {error && <p className="text-sm text-red-400 mb-4">{error}</p>}

        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {loading ? "Creating..." : "Create Link"}
          </button>
        </div>
      </div>
    </div>
  );
}
