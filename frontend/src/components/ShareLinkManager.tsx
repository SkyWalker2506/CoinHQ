"use client";

import { useEffect, useState } from "react";
import { getShareLinks, revokeShareLink } from "@/lib/api";
import type { Profile, ShareLink } from "@/lib/types";
import CreateShareLinkModal from "./CreateShareLinkModal";
import { events } from "@/lib/analytics";

interface Props {
  profiles: Profile[];
}

const BASE_URL =
  typeof window !== "undefined"
    ? window.location.origin
    : process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

export default function ShareLinkManager({ profiles }: Props) {
  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(
    profiles[0]?.id ?? null
  );
  const [links, setLinks] = useState<ShareLink[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [createdLink, setCreatedLink] = useState<ShareLink | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const loadLinks = async () => {
    const data = await getShareLinks(selectedProfileId ?? undefined).catch(() => []);
    setLinks(data);
  };

  useEffect(() => {
    loadLinks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProfileId]);

  const handleRevoke = async (id: number) => {
    if (!confirm("Revoke this share link? It will stop working immediately.")) return;
    await revokeShareLink(id);
    await loadLinks();
  };

  const copyUrl = (token: string) => {
    const url = `${BASE_URL}/share/${token}`;
    navigator.clipboard.writeText(url).then(() => {
      events.shareLinkCopied();
      setCopied(token);
      setTimeout(() => setCopied(null), 2000);
    });
  };

  const handleCreated = (link: ShareLink) => {
    setShowCreate(false);
    setCreatedLink(link);
    loadLinks();
  };

  const formatExpiry = (exp: string | null) => {
    if (!exp) return "No expiry";
    const d = new Date(exp);
    return d.toLocaleDateString();
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-lg font-semibold text-white">Share Links</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Share your portfolio without exposing API keys
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          + New Link
        </button>
      </div>

      {/* Profile filter */}
      {profiles.length > 1 && (
        <div className="flex gap-2 mb-4 flex-wrap">
          <button
            onClick={() => setSelectedProfileId(null)}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
              selectedProfileId === null
                ? "bg-blue-600 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            All profiles
          </button>
          {profiles.map((p) => (
            <button
              key={p.id}
              onClick={() => setSelectedProfileId(p.id)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                selectedProfileId === p.id
                  ? "bg-blue-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700"
              }`}
            >
              {p.name}
            </button>
          ))}
        </div>
      )}

      {/* Links list */}
      {links.length === 0 ? (
        <p className="text-sm text-gray-500 py-6 text-center">No active share links.</p>
      ) : (
        <div className="space-y-3">
          {links.map((link) => (
            <div
              key={link.id}
              className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-3"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  {link.label && (
                    <span className="text-sm font-medium text-white truncate">{link.label}</span>
                  )}
                  {!link.label && (
                    <span className="text-sm text-gray-400 font-mono truncate">
                      {`${BASE_URL}/share/${link.token.slice(0, 12)}…`}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 mt-1 flex-wrap">
                  <span className="text-xs text-gray-500">
                    Expires: {formatExpiry(link.expires_at)}
                  </span>
                  <span className="text-xs text-gray-600">
                    {[
                      link.show_total_value && "total",
                      link.show_coin_amounts && "amounts",
                      link.show_exchange_names && "exchanges",
                      link.show_allocation_pct && "%",
                    ]
                      .filter(Boolean)
                      .join(", ")}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 ml-3 shrink-0">
                <button
                  onClick={() => copyUrl(link.token)}
                  aria-label={`Copy URL for ${link.label || 'share link'}`}
                  className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-xs text-white rounded-lg transition-colors"
                >
                  {copied === link.token ? "Copied!" : "Copy URL"}
                </button>
                <button
                  onClick={() => handleRevoke(link.id)}
                  aria-label={`Revoke share link ${link.label || ''}`}
                  className="text-xs text-red-400 hover:text-red-300 px-2"
                >
                  Revoke
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* New link created — show URL */}
      {createdLink && (
        <div className="mt-4 bg-green-900/30 border border-green-700 rounded-lg p-4">
          <p className="text-sm font-medium text-green-300 mb-2">Link created!</p>
          <div className="flex items-center gap-3">
            <code className="text-xs text-green-400 break-all flex-1">
              {`${BASE_URL}/share/${createdLink.token}`}
            </code>
            <button
              onClick={() => copyUrl(createdLink.token)}
              className="px-3 py-1.5 bg-green-700 hover:bg-green-600 text-xs text-white rounded-lg shrink-0"
            >
              {copied === createdLink.token ? "Copied!" : "Copy"}
            </button>
          </div>
          <button
            onClick={() => setCreatedLink(null)}
            className="text-xs text-gray-500 mt-2 hover:text-gray-400"
          >
            Dismiss
          </button>
        </div>
      )}

      {showCreate && selectedProfileId !== null && (
        <CreateShareLinkModal
          profileId={selectedProfileId}
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
        />
      )}

      {showCreate && selectedProfileId === null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl p-6 max-w-sm w-full">
            <p className="text-white mb-4">Please select a profile first.</p>
            <button
              onClick={() => setShowCreate(false)}
              className="px-4 py-2 bg-gray-700 rounded-lg text-sm text-white"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
