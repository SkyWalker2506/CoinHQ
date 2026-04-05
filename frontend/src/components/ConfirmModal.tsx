"use client";

import { useEffect } from "react";
import { useFocusTrap } from "@/hooks/useFocusTrap";

interface ConfirmModalProps {
  isOpen: boolean
  title: string
  message: string
  confirmLabel?: string
  onConfirm: () => void
  onCancel: () => void
  destructive?: boolean
}

export function ConfirmModal({ isOpen, title, message, confirmLabel = 'Confirm', onConfirm, onCancel, destructive = false }: ConfirmModalProps) {
  const trapRef = useFocusTrap(isOpen);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => { if (e.key === 'Escape') onCancel() }
    if (isOpen) document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [isOpen, onCancel])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div ref={trapRef} role="dialog" aria-modal="true" aria-labelledby="confirm-title"
           className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-md w-full mx-4">
        <h2 id="confirm-title" className="text-lg font-semibold text-white mb-2">{title}</h2>
        <p className="text-gray-400 mb-6">{message}</p>
        <div className="flex gap-3 justify-end">
          <button onClick={onCancel} className="px-4 py-2 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700">
            Cancel
          </button>
          <button onClick={onConfirm}
            className={`px-4 py-2 rounded-lg font-medium ${destructive ? 'bg-red-600 hover:bg-red-700 text-white' : 'bg-blue-600 hover:bg-blue-700 text-white'}`}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
