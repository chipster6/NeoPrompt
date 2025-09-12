import React, { useEffect, useState } from 'react'
import { apiHistory } from '../lib/api'

export default function HistoryList() {
  const [items, setItems] = useState<any[]>([])
  useEffect(() => {
    apiHistory({ limit: 10 }).then((r) => setItems(r.items)).catch(() => setItems([]))
  }, [])

  if (!items.length) return null

  return (
    <div className="bg-neutral-950 p-3 rounded border border-green-900">
      <div className="text-green-400 mb-2">History</div>
      <div className="space-y-2 text-sm">
        {items.map((d) => (
          <div key={d.id} className="flex gap-3">
            <span className="text-green-600">{new Date(d.timestamp).toLocaleTimeString()}</span>
            <span>{d.assistant}</span>
            <span>{d.category}</span>
            <span className="truncate">{d.recipe_id}</span>
            <span>{d.reward ?? '-'}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

