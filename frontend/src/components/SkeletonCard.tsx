export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-6 animate-pulse">
      <div className="h-4 bg-gray-700 rounded w-1/3 mb-4" />
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-3 bg-gray-800 rounded mb-2" style={{ width: `${70 + i * 10}%` }} />
      ))}
    </div>
  )
}

export function PortfolioSkeleton() {
  return (
    <div className="space-y-4">
      <SkeletonCard lines={2} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SkeletonCard lines={4} />
        <SkeletonCard lines={4} />
      </div>
    </div>
  )
}
