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
  const [severityFilter, setSeverityFilter] = useState<'all' | 'error' | 'warning'>('all')
  const [pathQuery, setPathQuery] = useState('')

  useEffect(() => {
    if (!open) return
    refresh()
  }, [open])

  async function refresh() {
    setLoading(true)
    setError(null)
    try {
      // Call with explicit reload flag for clarity (backend treats all calls as reload today)
      const r = await apiRecipes(/* reload= */ true)
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
              {loading ? 'Reloading…' : 'Reload Prompt Templates'}
            </button>
            {error && <span className="text-red-400 text-sm">{error}</span>}
          </div>

          <div className="text-green-400">Loaded Prompt Templates & Validation</div>

          {recipes && (
            <div className="text-sm text-neutral-300 flex items-center gap-3">
              <span>Prompt Templates: <span className="text-green-400">{recipes.recipes?.length ?? 0}</span></span>
              <span>Diagnostics: <span className="text-green-400">{recipes.errors?.length ?? 0}</span></span>
            </div>
          )}

          <div className="flex items-center gap-2 text-sm mt-2">
            <label>Severity:</label>
            <select className="bg-neutral-900 px-2 py-1 rounded" value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value as any)}>
              <option value="all">All</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
            </select>
            <input
              className="bg-neutral-900 px-2 py-1 rounded flex-1"
              placeholder="Filter by file path"
              value={pathQuery}
              onChange={(e) => setPathQuery(e.target.value)}
            />
          </div>

          <div className="max-h-80 overflow-auto border border-green-900 rounded divide-y divide-green-900/30">
            {(recipes?.errors || [])
              .filter((e: any) => severityFilter === 'all' || e.severity === severityFilter)
              .filter((e: any) => !pathQuery || (e.file_path || '').toLowerCase().includes(pathQuery.toLowerCase()))
              .map((e: any, idx: number) => (
                <div key={idx} className="p-2 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <code className="text-neutral-300 truncate">{e.file_path}</code>
                    <div className="flex items-center gap-2">
                      {e.error_type && <span className="px-2 py-0.5 rounded bg-neutral-800 text-neutral-300 text-xs">{e.error_type}</span>}
                      {e.severity && <span className={`px-2 py-0.5 rounded text-xs ${e.severity === 'error' ? 'bg-red-900/60 text-red-300' : 'bg-yellow-900/60 text-yellow-300'}`}>{e.severity}</span>}
                      {Number.isFinite(e.line_number) && <span className="px-2 py-0.5 rounded bg-neutral-800 text-neutral-300 text-xs">line {e.line_number}</span>}
                    </div>
                  </div>
                  <div className="mt-1 text-neutral-400 whitespace-pre-wrap">{e.error}</div>
                </div>
              ))}
            {recipes && (recipes.errors || []).length === 0 && (
              <div className="p-2 text-neutral-400 text-sm">No diagnostics</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
