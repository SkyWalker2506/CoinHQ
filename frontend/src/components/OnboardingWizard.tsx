'use client'
import { useState } from 'react'

const steps = [
  { id: 1, title: 'Create your first profile', description: 'A profile groups your exchange accounts together.' },
  { id: 2, title: 'Connect an exchange', description: 'Add your read-only API keys from Binance, Bybit, or OKX.' },
  { id: 3, title: 'Share your portfolio', description: 'Create a shareable link to show your portfolio publicly.' },
]

export function OnboardingWizard({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState(0)

  const handleComplete = () => {
    localStorage.setItem('onboarding_done', 'true')
    onComplete()
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 max-w-lg w-full mx-4">
        <div className="flex gap-2 mb-6">
          {steps.map((s, i) => (
            <div key={s.id} className={`h-1 flex-1 rounded ${i <= step ? 'bg-blue-500' : 'bg-gray-700'}`} />
          ))}
        </div>
        <h2 className="text-xl font-bold text-white mb-2">{steps[step].title}</h2>
        <p className="text-gray-400 mb-8">{steps[step].description}</p>
        <div className="flex justify-between">
          <button onClick={handleComplete} className="text-gray-500 hover:text-gray-300 text-sm">
            Skip setup
          </button>
          <button
            onClick={() => step < steps.length - 1 ? setStep(step + 1) : handleComplete()}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
          >
            {step < steps.length - 1 ? 'Next →' : 'Get started'}
          </button>
        </div>
      </div>
    </div>
  )
}
