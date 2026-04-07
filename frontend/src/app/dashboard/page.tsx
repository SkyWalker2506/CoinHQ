"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getPortfolio, getAggregatePortfolio } from "@/lib/api";
import type { PortfolioResponse, AggregatePortfolioResponse } from "@/lib/types";
import { useProfiles } from "@/hooks/usePortfolio";
import ProfileSwitcher from "@/components/ProfileSwitcher";
import PortfolioSummary from "@/components/PortfolioSummary";
import dynamic from "next/dynamic";
import ExchangeList from "@/components/ExchangeList";
import Link from "next/link";
import { PortfolioSkeleton } from "@/components/SkeletonCard";
import { Navigation } from "@/components/Navigation";
import { OnboardingWizard } from "@/components/OnboardingWizard";
import { GlobalMarketBar } from "@/components/GlobalMarketBar";

function isAggregate(p: PortfolioResponse | AggregatePortfolioResponse): p is AggregatePortfolioResponse {
  return "grand_total_usd" in p;
}

const AllocationChart = dynamic(() => import("@/components/AllocationChart"), { ssr: false });

export default function DashboardPage() {
  const router = useRouter();
  const { profiles = [] } = useProfiles();
  const [selectedProfileId, setSelectedProfileId] = useState<number | "aggregate">("aggregate");
  const [portfolio, setPortfolio] = useState<PortfolioResponse | AggregatePortfolioResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) router.replace('/login')
  }, [router])

  useEffect(() => {
    const done = localStorage.getItem('onboarding_done')
    if (!done) setShowOnboarding(true)
  }, [])

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

  const totalUsd = portfolio
    ? isAggregate(portfolio) ? portfolio.grand_total_usd : portfolio.total_usd
    : 0;

  const exchanges = portfolio
    ? isAggregate(portfolio)
      ? portfolio.profiles?.flatMap((p) => p.exchanges) ?? []
      : portfolio.exchanges ?? []
    : [];

  return (
    <>
      {showOnboarding && <OnboardingWizard onComplete={() => setShowOnboarding(false)} />}
      <GlobalMarketBar />
      <Navigation />
    <div className="max-w-6xl mx-auto px-4 py-8">

      {/* Profile Switcher */}
      <ProfileSwitcher
        profiles={profiles}
        selected={selectedProfileId}
        onSelect={setSelectedProfileId}
      />

      {/* Error */}
      {error && (
        <div role="alert" className="mt-4 p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div role="status" aria-live="polite" aria-label="Portfolio yükleniyor" className="mt-8">
          <PortfolioSkeleton />
        </div>
      )}

      {/* Portfolio Content */}
      {!loading && portfolio && (
        <div className="mt-6 space-y-6">
          <PortfolioSummary
            totalUsd={totalUsd}
            cached={
              portfolio && isAggregate(portfolio)
                ? undefined
                : (portfolio as PortfolioResponse)?.cached
            }
          />

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
    </>
  );
}
