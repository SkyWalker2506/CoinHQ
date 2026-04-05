"use client";

interface Props {
  totalUsd: number;
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export default function PortfolioSummary({ totalUsd }: Props) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <p className="text-sm text-gray-400 mb-1">Total Portfolio Value</p>
      <p className="text-4xl font-bold text-white">{formatUsd(totalUsd)}</p>
    </div>
  );
}
