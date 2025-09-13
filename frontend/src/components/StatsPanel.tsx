import React, { useEffect, useMemo, useState } from 'react'
import { apiStatsGet, apiStatsUpdate } from '../lib/api'
import { useToast } from './ToastProvider'

interface Props {
  open: boolean
  onClose: () => void
}

export default function StatsPanel({ open, onClose }: Props) {
  const { showToast } = useToast()
  const [loading, setLoading] = useState(false)
  const [epsilon, setEpsilon] = useState(0.1)
  const [items, setItems] = useState<any[]>([])
  const [assistant, setAssistant] = useState('')
  const [category, setCategory] = useState('')

  useEffect(() => {
    if (!open) return
    refresh()
  }, [open])

  async function refresh() {
    setLoading(true)
    try {
      const r = await apiStatsGet({
        assistant: assistant || undefined,
        category: category || undefined,
      })
      setEpsilon(typeof r.epsilon === 'number' ? r.epsilon : 0.1)
      setItems(Array.isArray(r.items) ? r.items : [])
    } catch (e: any) {
      showToast(e?.message || 'Failed to load stats', 'error')
    } finally {
      setLoading(false)
    }
  }

  async function applyEpsilon(next: number) {
    setLoading(true)
    try {
      const r = await apiStatsUpdate({ epsilon: next })
      setEpsilon(r.epsilon)
      showToast(`Epsilon set to ${r.epsilon.toFixed(2)}`, 'success')
    } catch (e: any) {
      showToast(e?.message || 'Failed to update epsilon', 'error')
    } finally {
      setLoading(false)
    }
  }

  async function resetStats() {
    setLoading(true)
    try {
      const r = await apiStatsUpdate({
        reset: true,
        assistant: assistant || undefined,
        category: category || undefined,
      })
      setItems(Array.isArray(r.items) ? r.items : [])
      showToast('Stats reset', 'success')
    } catch (e: any) {
      showToast(e?.message || 'Failed to reset stats', 'error')
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <div className="relative z-10 w-full max-w-4xl rounded border border-green-900 bg-neutral-950 p-4 shadow-xl">
        <div className="flex items-center gap-2">
          <h2 className="text-green-400 text-lg">Optimizer Stats</h2>
          <div className="ml-auto flex items-center gap-2 text-sm">
            <select
              className="bg-neutral-900 px-2 py-1 rounded"
              value={assistant}
              onChange={(e) => setAssistant(e.target.value)}
              title="Filter by assistant"
            >
              <option value="">All assistants</option>
              {['chatgpt', 'claude', 'gemini', 'deepseek'].map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
            <select
              className="bg-neutral-900 px-2 py-1 rounded"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              title="Filter by category"
            >
              <option value="">All categories</option>
              {['coding', 'science', 'psychology', 'law', 'politics'].map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <button
              onClick={refresh}
              className="bg-neutral-800 hover:bg-neutral-700 px-3 py-1 rounded disabled:opacity-50"
              disabled={loading}
            >
              {loading ? 'Loading…' : 'Refresh'}
            </button>
          </div>
        </div>

        <div className="mt-3">
          <label className="text-sm text-green-300">Epsilon: {epsilon.toFixed(2)}</label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={epsilon}
            onChange={(e) => setEpsilon(parseFloat(e.target.value))}
            onMouseUp={() => applyEpsilon(epsilon)}
            onTouchEnd={() => applyEpsilon(epsilon)}
            className="w-full"
          />
        </div>

        <div className="mt-4 flex items-center gap-2">
          <button
            onClick={resetStats}
            className="bg-red-800 hover:bg-red-700 px-3 py-1 rounded disabled:opacity-50"
            disabled={loading}
          >
            Reset Stats {assistant || category ? '(filtered)' : '(all)'}
          </button>
          <span className="text-xs text-neutral-400">Deletes feedback rows to clear learned averages.</span>
        </div>

        <div className="mt-4">
          <div className="text-green-400">Mean reward per recipe</div>
          <div className="max-h-80 overflow-auto border border-green-900/40 rounded mt-2">
            <table className="w-full text-sm">
              <thead className="bg-neutral-900">
                <tr>
                  <th className="text-left p-2">Assistant</th>
                  <th className="text-left p-2">Category</th>
                  <th className="text-left p-2">Recipe</th>
                  <th className="text-right p-2">Mean</th>
                  <th className="text-right p-2">Count</th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 && (
                  <tr>
                    <td colSpan={5} className="p-3 text-neutral-400">
                      No stats yet.
                    </td>
                  </tr>
                )}
                {items.map((it) => (
                  <tr key={`${it.assistant}:${it.category}:${it.recipe_id}`} className="border-t border-green-900/20">
                    <td className="p-2">{it.assistant}</td>
                    <td className="p-2">{it.category}</td>
                    <td className="p-2 truncate" title={it.recipe_id}>
                      {it.recipe_id}
                    </td>
                    <td className="p-2 text-right">{Number(it.mean_reward).toFixed(3)}</td>
                    <td className="p-2 text-right">{it.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <button onClick={onClose} className="px-3 py-1 rounded bg-neutral-800 hover:bg-neutral-700">
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
