"use client";

import type { Profile } from "@/lib/types";

interface Props {
  profiles: Profile[];
  selected: number | "aggregate";
  onSelect: (id: number | "aggregate") => void;
}

export default function ProfileSwitcher({ profiles, selected, onSelect }: Props) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <button
        onClick={() => onSelect("aggregate")}
        className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
          selected === "aggregate"
            ? "bg-blue-600 text-white"
            : "bg-gray-800 text-gray-300 hover:bg-gray-700"
        }`}
      >
        All Profiles
      </button>
      {profiles.map((p) => (
        <button
          key={p.id}
          onClick={() => onSelect(p.id)}
          className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
            selected === p.id
              ? "bg-blue-600 text-white"
              : "bg-gray-800 text-gray-300 hover:bg-gray-700"
          }`}
        >
          {p.name}
        </button>
      ))}
    </div>
  );
}
