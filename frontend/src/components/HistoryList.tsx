import React, { useEffect, useMemo, useState } from 'react'
import { apiHistory } from '../lib/api'

const ASSISTANTS = ['chatgpt', 'claude', 'gemini', 'deepseek']
const CATEGORIES = ['coding', 'science', 'psychology', 'law', 'politics']

export default function HistoryList({ defaultWithText = false }: { defaultWithText?: boolean }) {
  const [items, setItems] = useState<any[]>([])
  const [limit, setLimit] = useState(10)
  const [assistant, setAssistant] = useState<string>('')
  const [category, setCategory] = useState<string>('')
  const [withText, setWithText] = useState<boolean>(defaultWithText)
  const [loading, setLoading] = useState(false)

  const params = useMemo(
    () => ({ limit, assistant: assistant || undefined, category: category || undefined, with_text: withText }),
    [limit, assistant, category, withText]
  )

  useEffect(() => {
    let active = true
    setLoading(true)
    apiHistory(params)
      .then((r) => {
        if (!active) return
        setItems(Array.isArray(r.items) ? r.items : [])
      })
      .catch(() => active && setItems([]))
      .finally(() => active && setLoading(false))
    return () => {
      active = false
    }
  }, [params.limit, params.assistant, params.category, params.with_text])

  return (
    <div className="bg-neutral-950 p-3 rounded border border-green-900">
      <div className="flex items-center gap-2 mb-2">
        <div className="text-green-400 mr-2">History</div>
        <select
          className="bg-neutral-900 px-2 py-1 rounded text-sm"
          value={assistant}
          onChange={(e) => setAssistant(e.target.value)}
          title="Filter by assistant"
        >
          <option value="">All assistants</option>
          {ASSISTANTS.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
        <select
          className="bg-neutral-900 px-2 py-1 rounded text-sm"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          title="Filter by category"
        >
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <label className="ml-auto flex items-center gap-2 text-sm">
          <input type="checkbox" checked={withText} onChange={(e) => setWithText(e.target.checked)} /> with_text
        </label>
      </div>

      <div className="space-y-2 text-sm min-h-[2rem]">
        {!items.length && !loading && <div className="text-neutral-400">No history.</div>}
        {items.map((d) => (
          <div key={d.id} className="flex flex-col gap-1 border-b border-green-900/30 pb-2">
            <div className="flex gap-3 items-center">
              <span className="text-green-600">{new Date(d.timestamp).toLocaleTimeString()}</span>
              <span>{d.assistant}</span>
              <span>{d.category}</span>
              <span className="truncate" title={d.recipe_id}>{d.recipe_id}</span>
              <span className="ml-auto">{d.reward ?? '-'}</span>
            </div>
            {withText && (d.raw_input || d.engineered_prompt) && (
              <div className="text-xs text-green-200/80 max-w-full truncate" title={(d.raw_input || d.engineered_prompt) as string}>
                {(d.raw_input || d.engineered_prompt) as string}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="mt-3 flex items-center gap-3">
        <button
          className="bg-neutral-800 hover:bg-neutral-700 px-3 py-1 rounded disabled:opacity-50"
          onClick={() => setLimit((n) => n + 10)}
          disabled={loading}
        >
          {loading ? 'Loading…' : 'Load more'}
        </button>
        <span className="text-xs text-neutral-400">Showing {items.length} item(s)</span>
      </div>
    </div>
  )
}

