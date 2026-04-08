"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getProfiles, deleteProfile, getKeys, deleteKey } from "@/lib/api";
import type { Profile, ExchangeKey } from "@/lib/types";
import AddProfileModal from "@/components/AddProfileModal";
import AddKeyModal from "@/components/AddKeyModal";
import ShareLinkManager from "@/components/ShareLinkManager";
import { Navigation } from "@/components/Navigation";
import { ConfirmModal } from "@/components/ConfirmModal";
import { UpgradeBanner } from "@/components/UpgradeBanner";

export default function SettingsPage() {
  const router = useRouter();
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [keys, setKeys] = useState<Record<number, ExchangeKey[]>>({});
  const [showAddProfile, setShowAddProfile] = useState(false);
  const [addKeyForProfile, setAddKeyForProfile] = useState<number | null>(null);
  const [confirmAction, setConfirmAction] = useState<{
    title: string;
    message: string;
    onConfirm: () => void;
  } | null>(null);
  const [tierLimitMessage, setTierLimitMessage] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) router.replace('/login')
  }, [router])

  const loadProfiles = async () => {
    const p = await getProfiles();
    setProfiles(p);
    const keyMap: Record<number, ExchangeKey[]> = {};
    await Promise.all(
      p.map(async (profile) => {
        keyMap[profile.id] = await getKeys(profile.id).catch(() => []);
      })
    );
    setKeys(keyMap);
  };

  useEffect(() => {
    loadProfiles();
  }, []);

  const handleDeleteProfile = (id: number) => {
    setConfirmAction({
      title: "Delete Profile",
      message: "Delete this profile and all its API keys? This action cannot be undone.",
      onConfirm: async () => {
        setConfirmAction(null);
        await deleteProfile(id);
        await loadProfiles();
      },
    });
  };

  const handleDeleteKey = (profileId: number, keyId: number) => {
    setConfirmAction({
      title: "Remove API Key",
      message: "Remove this API key? You can always add it again later.",
      onConfirm: async () => {
        setConfirmAction(null);
        await deleteKey(profileId, keyId);
        await loadProfiles();
      },
    });
  };

  return (
    <>
      <Navigation />
    <div className="max-w-4xl mx-auto px-4 py-6 sm:py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 sm:mb-8">
        <h1 className="text-xl sm:text-2xl font-bold text-white">Settings</h1>
        <button
          onClick={() => setShowAddProfile(true)}
          className="px-3 py-2 sm:px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Add Profile
        </button>
      </div>

      {/* Tier limit banner */}
      {tierLimitMessage && (
        <div className="mb-6">
          <UpgradeBanner message={tierLimitMessage} />
        </div>
      )}

      {/* Profiles list */}
      <div className="space-y-4">
        {profiles.length === 0 && (
          <div className="text-center text-gray-400 py-16">
            No profiles yet. Create one to get started.
          </div>
        )}
        {profiles.map((profile) => (
          <div
            key={profile.id}
            className="bg-gray-900 border border-gray-800 rounded-xl p-4 sm:p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">{profile.name}</h2>
              <button
                onClick={() => handleDeleteProfile(profile.id)}
                aria-label={`Delete profile ${profile.name}`}
                className="text-xs text-red-400 hover:text-red-300"
              >
                Delete profile
              </button>
            </div>

            {/* Exchange keys */}
            <div className="space-y-2 mb-4">
              {(keys[profile.id] ?? []).length === 0 && (
                <p className="text-sm text-gray-500">No API keys added yet.</p>
              )}
              {(keys[profile.id] ?? []).map((key) => (
                <div
                  key={key.id}
                  className="flex items-center justify-between bg-gray-800 rounded-lg px-3 sm:px-4 py-2"
                >
                  <div>
                    <span className="text-sm font-medium text-white capitalize">
                      {key.exchange}
                    </span>
                    <span className="text-xs text-gray-500 ml-3">
                      Added {new Date(key.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <button
                    onClick={() => handleDeleteKey(profile.id, key.id)}
                    aria-label={`Remove ${key.exchange} API key`}
                    className="text-xs text-red-400 hover:text-red-300"
                  >
                    Remove
                  </button>
                </div>
              ))}
            </div>

            <button
              onClick={() => setAddKeyForProfile(profile.id)}
              className="text-sm text-blue-400 hover:text-blue-300 font-medium"
            >
              + Add API Key
            </button>
          </div>
        ))}
      </div>

      {/* Share Links */}
      <div className="mt-8">
        <ShareLinkManager profiles={profiles} />
      </div>

      {/* Modals */}
      {showAddProfile && (
        <AddProfileModal
          onClose={() => setShowAddProfile(false)}
          onCreated={loadProfiles}
          onTierLimit={(msg) => setTierLimitMessage(msg)}
        />
      )}
      {addKeyForProfile !== null && (
        <AddKeyModal
          profileId={addKeyForProfile}
          onClose={() => setAddKeyForProfile(null)}
          onAdded={loadProfiles}
        />
      )}
      <ConfirmModal
        isOpen={confirmAction !== null}
        title={confirmAction?.title ?? ""}
        message={confirmAction?.message ?? ""}
        confirmLabel="Delete"
        destructive
        onConfirm={confirmAction?.onConfirm ?? (() => {})}
        onCancel={() => setConfirmAction(null)}
      />
    </div>
    </>
  );
}
