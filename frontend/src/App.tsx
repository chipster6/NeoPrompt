import React, { useEffect, useMemo, useState } from 'react'
import { apiChoose, apiFeedback, apiHistory, apiRecipes } from './lib/api'
import Console from './components/Console'
import OutputPanel from './components/OutputPanel'
import HistoryList from './components/HistoryList'

export default function App() {
  const [assistant, setAssistant] = useState('chatgpt')
  const [category, setCategory] = useState('coding')
  const [enhance, setEnhance] = useState(false)
  const [raw, setRaw] = useState('')
  const [result, setResult] = useState<any>(null)
  const [recipes, setRecipes] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    apiRecipes().then((r) => setRecipes(r.recipes)).catch(() => setRecipes([]))
  }, [])

  async function onGenerate() {
    setLoading(true)
    try {
      const res = await apiChoose({
        assistant,
        category,
        raw_input: raw,
        options: { enhance, force_json: false },
        context_features: {},
      })
      setResult(res)
    } finally {
      setLoading(false)
    }
  }

  async function onLike(like: boolean) {
    if (!result) return
    await apiFeedback({
      decision_id: result.decision_id,
      reward_components: { user_like: like ? 1 : 0 },
      reward: like ? 1 : 0,
      safety_flags: [],
    })
  }

  return (
    <div className="min-h-screen p-4 bg-black text-green-300">
      <div className="max-w-5xl mx-auto space-y-4">
        <div className="flex items-center gap-3">
          <select value={assistant} onChange={(e) => setAssistant(e.target.value)} className="bg-neutral-900 px-3 py-2 rounded">
            <option value="chatgpt">ChatGPT</option>
            <option value="claude">Claude</option>
            <option value="gemini">Gemini</option>
            <option value="deepseek">DeepSeek</option>
          </select>
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="bg-neutral-900 px-3 py-2 rounded">
            <option value="coding">Coding</option>
            <option value="science">Science</option>
            <option value="psychology">Psychology</option>
            <option value="law">Law</option>
            <option value="politics">Politics</option>
          </select>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={enhance} onChange={(e) => setEnhance(e.target.checked)} /> Enhance
          </label>
          <button onClick={onGenerate} className="ml-auto bg-green-700 hover:bg-green-600 px-4 py-2 rounded disabled:opacity-50" disabled={loading}>
            {loading ? 'Generating...' : 'Generate'}
          </button>
        </div>

        <Console value={raw} onChange={setRaw} onSubmit={onGenerate} />
        <OutputPanel result={result} onLike={onLike} />
        <HistoryList />
      </div>
    </div>
  )
}

