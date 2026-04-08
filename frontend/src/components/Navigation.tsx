'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const navItems = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/trading', label: 'Trading' },
  { href: '/settings', label: 'Settings' },
]

export function Navigation() {
  const pathname = usePathname()

  const handleLogout = () => {
    localStorage.removeItem('token')
    window.location.href = '/login'
  }

  return (
    <nav className="border-b border-gray-800 bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <span className="font-bold text-white text-lg">CoinHQ</span>
          <div className="flex gap-1">
            {navItems.map(item => (
              <Link key={item.href} href={item.href}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  pathname === item.href
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`}>
                {item.label}
              </Link>
            ))}
          </div>
        </div>
        <button onClick={handleLogout} className="text-gray-500 hover:text-gray-300 text-sm">
          Sign out
        </button>
      </div>
    </nav>
  )
}
