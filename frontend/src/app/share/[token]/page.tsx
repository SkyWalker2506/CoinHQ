import type { Metadata } from "next";
import type { SharedPortfolioView } from "@/lib/types";
import FollowButton from "@/components/FollowButton";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function generateMetadata({ params }: { params: Promise<{ token: string }> }): Promise<Metadata> {
  const { token } = await params;
  try {
    const res = await fetch(`${BASE_URL}/api/v1/public/share/${token}`, { next: { revalidate: 60 } })
    if (res.ok) {
      const data = await res.json()
      const profileName = data.profile_name || 'Crypto Portfolio'
      return {
        title: `${profileName} — CoinHQ`,
        description: `View ${profileName}'s crypto portfolio on CoinHQ`,
        openGraph: {
          title: `${profileName} — CoinHQ`,
          description: `View ${profileName}'s crypto portfolio`,
        },
      }
    }
  } catch {}
  return {
    title: 'Crypto Portfolio — CoinHQ',
  }
}

async function fetchShare(token: string): Promise<SharedPortfolioView | null> {
  try {
    const res = await fetch(`${BASE_URL}/api/v1/public/share/${token}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

function fmt(val: number | null | undefined, prefix = "$"): string {
  if (val == null) return "—";
  return `${prefix}${val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function fmtPct(val: number | null | undefined): string {
  if (val == null) return "—";
  return `${val.toFixed(2)}%`;
}

export default async function SharePage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  const data = await fetchShare(token);

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-white mb-3">Link not available</h1>
          <p className="text-gray-400 text-sm">
            This link has expired, been revoked, or does not exist.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <span className="font-bold text-lg text-blue-400">CoinHQ</span>
          <div className="flex items-center gap-3">
            {data.allow_follow && <FollowButton token={token} />}
            <span className="text-xs text-gray-500 bg-gray-800 px-3 py-1 rounded-full hidden sm:inline">
              Read-only view
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        {/* Total */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 mb-6 text-center">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Total Portfolio Value</p>
          <p className="text-4xl font-bold">
            {data.total_usd != null ? fmt(data.total_usd) : "—"}
          </p>
          {!data.show_total_value && (
            <p className="text-xs text-gray-600 mt-2">Total value is hidden by the link owner</p>
          )}
        </div>

        {/* Exchanges */}
        <div className="space-y-4">
          {data.exchanges.map((ex, i) => (
            <div
              key={i}
              className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden"
            >
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800">
                <h2 className="font-semibold text-white">{ex.exchange_name}</h2>
                {ex.total_usd != null && (
                  <span className="text-sm text-gray-300">{fmt(ex.total_usd)}</span>
                )}
              </div>

              {ex.assets.length === 0 ? (
                <p className="text-sm text-gray-600 px-5 py-4">No assets</p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-gray-500 border-b border-gray-800">
                      <th className="px-5 py-2 text-left font-medium">Asset</th>
                      {data.show_coin_amounts && (
                        <th className="px-5 py-2 text-right font-medium">Amount</th>
                      )}
                      <th className="px-5 py-2 text-right font-medium">Value</th>
                      {data.show_allocation_pct && (
                        <th className="px-5 py-2 text-right font-medium">Allocation</th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {ex.assets.map((asset, j) => (
                      <tr
                        key={j}
                        className="border-b border-gray-800/50 last:border-0 hover:bg-gray-800/30"
                      >
                        <td className="px-5 py-3 font-medium text-white">{asset.asset}</td>
                        {data.show_coin_amounts && (
                          <td className="px-5 py-3 text-right text-gray-300">
                            {asset.amount != null
                              ? asset.amount.toLocaleString("en-US", { maximumFractionDigits: 6 })
                              : "—"}
                          </td>
                        )}
                        <td className="px-5 py-3 text-right text-gray-300">
                          {fmt(asset.usd_value)}
                        </td>
                        {data.show_allocation_pct && (
                          <td className="px-5 py-3 text-right text-gray-400">
                            {fmtPct(asset.allocation_pct)}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          ))}
        </div>

        <p className="text-center text-xs text-gray-600 mt-8">
          Generated by CoinHQ — read-only shared view. Exchange API secrets are never exposed.
        </p>

        <div className="mt-8 pt-6 border-t border-gray-800 text-center">
          <p className="text-gray-500 text-sm mb-3">Track your own crypto portfolio</p>
          <a href="/" className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-colors">
            Start with CoinHQ — Free
          </a>
          <p className="text-gray-600 text-xs mt-3">Powered by CoinHQ</p>
        </div>
      </main>
    </div>
  );
}
