"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Navigation } from "@/components/Navigation";
import dynamic from "next/dynamic";

const TechnicalAnalysis = dynamic(() => import("@/components/TechnicalAnalysis"), { ssr: false });
const BacktestPanel = dynamic(() => import("@/components/BacktestPanel"), { ssr: false });

export default function TradingPage() {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) router.replace("/login");
  }, [router]);

  return (
    <>
      <Navigation />
      <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
        <h1 className="text-2xl font-bold text-white">Trading Analysis</h1>
        <p className="text-gray-400 text-sm">
          Powered by TradingView — real-time technical indicators, multi-timeframe analysis, and strategy backtesting.
        </p>
        <TechnicalAnalysis />
        <BacktestPanel />
      </div>
    </>
  );
}
