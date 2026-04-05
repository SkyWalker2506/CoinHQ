"use client";

interface Props {
  totalUsd: number;
  cached?: boolean;
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export default function PortfolioSummary({ totalUsd, cached }: Props) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <div className="flex items-center gap-3 mb-1">
        <p className="text-sm text-gray-400">Total Portfolio Value</p>
        {cached === true && (
          <span className="inline-flex items-center gap-1 text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full border border-gray-700">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            Cached · refreshing...
          </span>
        )}
        {cached === false && (
          <span className="inline-flex items-center gap-1 text-xs text-green-600 bg-gray-800 px-2 py-0.5 rounded-full border border-gray-700">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
            Live
          </span>
        )}
      </div>
      <p className="text-4xl font-bold text-white">{formatUsd(totalUsd)}</p>
    </div>
  );
}
