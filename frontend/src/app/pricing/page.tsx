import WaitlistForm from '@/components/WaitlistForm'

export default function PricingPage() {
  const plans = [
    {
      name: 'Self-Hosted',
      price: 'Free',
      description: 'Host on your own server',
      features: ['Unlimited profiles', 'All exchanges', 'Full control', 'Open source'],
      cta: 'View on GitHub',
      href: 'https://github.com',
      highlight: false,
    },
    {
      name: 'Cloud Free',
      price: '$0/mo',
      description: 'Hosted by us, free forever',
      features: ['1 profile', '2 exchanges', 'Share links', 'Auto updates'],
      cta: 'Get started',
      href: '/login',
      highlight: false,
    },
    {
      name: 'Cloud Premium',
      price: '$9/mo',
      description: 'Full featured cloud hosting',
      features: ['Unlimited profiles', 'All 5 exchanges', 'Priority support', 'Delegated trading (coming)'],
      cta: 'Join waitlist',
      href: '#waitlist',
      highlight: true,
    },
  ]

  return (
    <div className="min-h-screen bg-gray-950 py-16 px-4">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-4xl font-bold text-white text-center mb-4">Simple pricing</h1>
        <p className="text-gray-400 text-center mb-12">Self-host for free, or use our cloud</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map(plan => (
            <div key={plan.name} className={`rounded-2xl border p-6 ${plan.highlight ? 'border-blue-500 bg-blue-950/20' : 'border-gray-800 bg-gray-900'}`}>
              <h2 className="text-xl font-bold text-white mb-1">{plan.name}</h2>
              <div className="text-3xl font-bold text-white mb-1">{plan.price}</div>
              <p className="text-gray-500 text-sm mb-6">{plan.description}</p>
              <ul className="space-y-2 mb-8">
                {plan.features.map(f => (
                  <li key={f} className="flex items-center gap-2 text-gray-300 text-sm">
                    <span className="text-green-500">&#10003;</span> {f}
                  </li>
                ))}
              </ul>
              <a href={plan.href} className={`block text-center py-2.5 rounded-xl font-medium transition-colors ${plan.highlight ? 'bg-blue-600 hover:bg-blue-700 text-white' : 'bg-gray-800 hover:bg-gray-700 text-gray-200'}`}>
                {plan.cta}
              </a>
            </div>
          ))}
        </div>
        <WaitlistForm />
      </div>
    </div>
  )
}
