import React, { useEffect, useState } from 'react'
import { apiRecipes } from '../lib/api'

interface Props {
  open: boolean
  onClose: () => void
  storeText: boolean
  onToggleStoreText: (v: boolean) => void
  tokenCostPerK: number
  onUpdateTokenCostPerK: (v: number) => void
}

export default function SettingsModal({ open, onClose, storeText, onToggleStoreText, tokenCostPerK, onUpdateTokenCostPerK }: Props) {
  const [loading, setLoading] = useState(false)
  const [recipes, setRecipes] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    refresh()
  }, [open])

  async function refresh() {
    setLoading(true)
    setError(null)
    try {
      const r = await apiRecipes()
      setRecipes(r)
    } catch (e: any) {
      setError(e?.message || 'Failed to load recipes')
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div className="relative z-10 w-full max-w-3xl rounded border border-green-900 bg-neutral-950 p-4 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="text-green-400 text-lg">Settings & Diagnostics</h2>
          <button onClick={onClose} className="px-2 py-1 rounded hover:bg-neutral-800">✕</button>
        </div>

        <div className="mt-4 space-y-4">
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={storeText}
                  onChange={(e) => onToggleStoreText(e.target.checked)}
                />
                STORE_TEXT (frontend preference)
              </label>
              <span className="text-xs text-neutral-400">
                If enabled and supported by backend, raw/engineered text may be stored and retrievable in history.
              </span>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-sm text-neutral-300">Token cost ($/1K):</label>
              <input
                type="number"
                step="0.0001"
                min="0"
                className="bg-neutral-900 px-2 py-1 rounded text-sm w-32"
                value={Number.isFinite(tokenCostPerK) ? tokenCostPerK : 0}
                onChange={(e) => onUpdateTokenCostPerK(Math.max(0, Number(e.target.value)))}
                placeholder="0.0000"
              />
              <span className="text-xs text-neutral-400">Used for cost estimate display</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button onClick={refresh} className="bg-green-700 hover:bg-green-600 px-3 py-1 rounded disabled:opacity-50" disabled={loading}>
              {loading ? 'Reloading…' : 'Reload Recipes'}
            </button>
            {error && <span className="text-red-400 text-sm">{error}</span>}
          </div>

          <div className="text-green-400">Loaded Recipes & Validation</div>
          <pre className="max-h-80 overflow-auto whitespace-pre-wrap text-green-200 bg-black/40 p-2 rounded border border-green-900">
            {recipes ? JSON.stringify(recipes, null, 2) : 'No data'}
          </pre>
        </div>
      </div>
    </div>
  )
}
