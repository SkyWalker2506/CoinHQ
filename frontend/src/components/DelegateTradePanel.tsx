"use client";

import { delegateTrade } from "@/lib/api";
import TradePanel from "./TradePanel";
import type { TradeDirection, TradeOrderRequest } from "@/lib/types";

interface Props {
  token: string;
  exchanges: string[];
  direction: TradeDirection;
  allowedCoins: string | null;
  maxPerOrderUsd: number | null;
  dailyLimitUsd: number | null;
  spentTodayUsd: number;
}

export default function DelegateTradePanel({
  token,
  exchanges,
  direction,
  allowedCoins,
  maxPerOrderUsd,
  dailyLimitUsd,
  spentTodayUsd,
}: Props) {
  return (
    <div className="bg-gray-900 border border-amber-500/30 rounded-2xl p-6 mb-6">
      <div className="flex items-center gap-2 mb-1">
        <h2 className="font-semibold text-white">Trade on this portfolio</h2>
        <span className="text-[10px] font-semibold uppercase tracking-wide bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded-full">
          Delegated
        </span>
      </div>
      <p className="text-xs text-gray-500 mb-4">
        You can place spot buy/sell orders within the owner&apos;s limits. Withdrawals are never possible.
      </p>
      <TradePanel
        exchanges={exchanges}
        direction={direction}
        allowedCoins={allowedCoins}
        maxPerOrderUsd={maxPerOrderUsd}
        dailyLimitUsd={dailyLimitUsd}
        spentTodayUsd={spentTodayUsd}
        onSubmit={(payload: TradeOrderRequest) => delegateTrade(token, payload)}
      />
    </div>
  );
}
