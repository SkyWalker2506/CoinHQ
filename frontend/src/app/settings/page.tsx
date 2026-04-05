"use client";

import { useEffect, useState } from "react";
import { getProfiles, deleteProfile, getKeys, deleteKey } from "@/lib/api";
import type { Profile, ExchangeKey } from "@/lib/types";
import AddProfileModal from "@/components/AddProfileModal";
import AddKeyModal from "@/components/AddKeyModal";
import ShareLinkManager from "@/components/ShareLinkManager";
import Link from "next/link";

export default function SettingsPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [keys, setKeys] = useState<Record<number, ExchangeKey[]>>({});
  const [showAddProfile, setShowAddProfile] = useState(false);
  const [addKeyForProfile, setAddKeyForProfile] = useState<number | null>(null);

  const loadProfiles = async () => {
    const p = await getProfiles();
    setProfiles(p);
    // Load keys for each profile
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

  const handleDeleteProfile = async (id: number) => {
    if (!confirm("Delete this profile and all its API keys?")) return;
    await deleteProfile(id);
    await loadProfiles();
  };

  const handleDeleteKey = async (profileId: number, keyId: number) => {
    if (!confirm("Remove this API key?")) return;
    await deleteKey(profileId, keyId);
    await loadProfiles();
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <Link href="/dashboard" className="text-sm text-gray-400 hover:text-white">
            ← Dashboard
          </Link>
          <h1 className="text-2xl font-bold text-white mt-1">Settings</h1>
        </div>
        <button
          onClick={() => setShowAddProfile(true)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Add Profile
        </button>
      </div>

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
            className="bg-gray-900 border border-gray-800 rounded-xl p-6"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">{profile.name}</h2>
              <button
                onClick={() => handleDeleteProfile(profile.id)}
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
                  className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-2"
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
        />
      )}
      {addKeyForProfile !== null && (
        <AddKeyModal
          profileId={addKeyForProfile}
          onClose={() => setAddKeyForProfile(null)}
          onAdded={loadProfiles}
        />
      )}
    </div>
  );
}
