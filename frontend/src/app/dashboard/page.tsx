"use client";

import { useEffect, useState } from "react";
import { getProfiles, getPortfolio, getAggregatePortfolio } from "@/lib/api";
import type { Profile, PortfolioResponse, AggregatePortfolioResponse } from "@/lib/types";
import ProfileSwitcher from "@/components/ProfileSwitcher";
import PortfolioSummary from "@/components/PortfolioSummary";
import AllocationChart from "@/components/AllocationChart";
import ExchangeList from "@/components/ExchangeList";
import Link from "next/link";

export default function DashboardPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<number | "aggregate">("aggregate");
  const [portfolio, setPortfolio] = useState<PortfolioResponse | AggregatePortfolioResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProfiles().then(setProfiles).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const fetch =
      selectedProfileId === "aggregate"
        ? getAggregatePortfolio()
        : getPortfolio(selectedProfileId);

    fetch
      .then(setPortfolio)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [selectedProfileId]);

  const isAggregate = selectedProfileId === "aggregate";
  const totalUsd = isAggregate
    ? (portfolio as AggregatePortfolioResponse)?.grand_total_usd ?? 0
    : (portfolio as PortfolioResponse)?.total_usd ?? 0;

  const exchanges = isAggregate
    ? (portfolio as AggregatePortfolioResponse)?.profiles?.flatMap((p) => p.exchanges) ?? []
    : (portfolio as PortfolioResponse)?.exchanges ?? [];

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-white">CoinHQ</h1>
        <Link
          href="/settings"
          className="text-sm text-gray-400 hover:text-white transition-colors"
        >
          Settings
        </Link>
      </div>

      {/* Profile Switcher */}
      <ProfileSwitcher
        profiles={profiles}
        selected={selectedProfileId}
        onSelect={setSelectedProfileId}
      />

      {/* Error */}
      {error && (
        <div className="mt-4 p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="mt-8 text-center text-gray-400">Loading portfolio...</div>
      )}

      {/* Portfolio Content */}
      {!loading && portfolio && (
        <div className="mt-6 space-y-6">
          <PortfolioSummary totalUsd={totalUsd} />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <AllocationChart exchanges={exchanges} />
            <ExchangeList exchanges={exchanges} />
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && profiles.length === 0 && (
        <div className="mt-16 text-center text-gray-400">
          <p className="text-lg">No profiles yet.</p>
          <p className="mt-2">
            Go to{" "}
            <Link href="/settings" className="text-blue-400 hover:text-blue-300 underline">
              Settings
            </Link>{" "}
            to create a profile and add your API keys.
          </p>
        </div>
      )}
    </div>
  );
}
