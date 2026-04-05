"use client";

import { useState } from "react";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function FollowButton({ token }: { token: string }) {
  const [state, setState] = useState<"idle" | "loading" | "done" | "login">("idle");

  const handleFollow = async () => {
    const jwt = localStorage.getItem("token");
    if (!jwt) {
      setState("login");
      return;
    }
    setState("loading");
    try {
      const res = await fetch(`${BASE_URL}/api/v1/followed/${token}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${jwt}` },
      });
      if (res.ok || res.status === 409) {
        setState("done");
      } else {
        setState("idle");
        alert("Takip edilemedi. Lütfen tekrar deneyin.");
      }
    } catch {
      setState("idle");
    }
  };

  if (state === "done") {
    return (
      <span className="inline-flex items-center gap-2 px-5 py-2.5 bg-green-700/30 border border-green-600 text-green-400 rounded-xl text-sm font-medium">
        ✓ Portfolyonuza eklendi
      </span>
    );
  }

  if (state === "login") {
    return (
      <div className="text-center">
        <p className="text-sm text-gray-400 mb-3">Takip etmek için giriş yapmanız gerekiyor</p>
        <a
          href={`${BASE_URL}/api/v1/auth/google`}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-medium transition-colors"
        >
          Google ile Giriş Yap
        </a>
      </div>
    );
  }

  return (
    <button
      onClick={handleFollow}
      disabled={state === "loading"}
      className="inline-flex items-center gap-2 px-5 py-2.5 bg-gray-800 hover:bg-gray-700 border border-gray-600 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
    >
      {state === "loading" ? (
        <span className="w-4 h-4 border-2 border-gray-400 border-t-white rounded-full animate-spin" />
      ) : (
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
      )}
      Portfolyoma Ekle
    </button>
  );
}
