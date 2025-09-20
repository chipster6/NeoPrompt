import React, { useEffect, useMemo, useState } from 'react'
import { apiChoose, apiFeedback, apiRecipes } from './lib/api'
import Console from './components/Console'
import OutputPanel from './components/OutputPanel'
import HistoryList from './components/HistoryList'
import SettingsModal from './components/SettingsModal'
import StatsPanel from './components/StatsPanel'
import { useToast } from './components/ToastProvider'

export default function App() {
  return <AppImpl />
}

export function AppImpl() {
  const { showToast } = useToast()
  const [assistant, setAssistant] = useState('chatgpt')
  const [category, setCategory] = useState('coding')
  const [enhance, setEnhance] = useState(false)
  const [forceJson, setForceJson] = useState(false)
  const [raw, setRaw] = useState('')
  const [result, setResult] = useState<any>(null)
  const [recipes, setRecipes] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [statsOpen, setStatsOpen] = useState(false)
  const [storeText, setStoreText] = useState<boolean>(() => {
    const v = localStorage.getItem('store_text')
    return v === '1'
  })
  const [tokenCostPerK, setTokenCostPerK] = useState<number>(() => {
    const v = localStorage.getItem('token_cost_per_k')
    const n = v ? Number(v) : 0
    return Number.isFinite(n) ? n : 0
  })
  // UI indicator: if user requests enhancement but backend enhancer is disabled, show a subtle badge
  const [serverEnhancerOff, setServerEnhancerOff] = useState(false)

  useEffect(() => {
    apiRecipes()
      .then((r) => setRecipes(Array.isArray(r.recipes) ? r.recipes : []))
      .catch(() => setRecipes([]))
  }, [])

  useEffect(() => {
    localStorage.setItem('store_text', storeText ? '1' : '0')
  }, [storeText])

  useEffect(() => {
    localStorage.setItem('token_cost_per_k', String(tokenCostPerK || 0))
  }, [tokenCostPerK])

  async function onGenerate() {
    if (!raw.trim()) {
      showToast('Enter some input first', 'error')
      return
    }
    setLoading(true)
    try {
      const res = await apiChoose({
        assistant,
        category,
        raw_input: raw,
        options: { enhance, force_json: forceJson },
        context_features: { store_text: storeText },
      })
      setResult(res)
      // If user asked for enhance but backend did not enhance, surface a subtle indicator
      const enhanced = Array.isArray(res?.notes) && res.notes.includes('enhanced=true')
      setServerEnhancerOff(!!enhance && !enhanced)
      showToast('Prompt generated', 'success')
    } catch (e: any) {
      showToast(e?.message || 'Failed to generate', 'error')
    } finally {
      setLoading(false)
    }
  }

  async function onLike(like: boolean) {
    if (!result) return
    try {
      await apiFeedback({
        decision_id: result.decision_id,
        reward_components: { user_like: like ? 1 : 0 },
        reward: like ? 1 : 0,
        safety_flags: [],
      })
      showToast(like ? 'Thanks for the thumbs up!' : 'Thanks for the feedback', 'success')
    } catch (e: any) {
      showToast('Feedback failed', 'error')
    }
  }

  async function onCopy(text: string) {
    try {
      await navigator.clipboard.writeText(text)
      showToast('Copied to clipboard', 'success')
      if (result?.decision_id) {
        try {
          await apiFeedback({
            decision_id: result.decision_id,
            reward_components: { copied: 1 },
            reward: 1,
            safety_flags: [],
          })
        } catch {
          // non-fatal
        }
      }
    } catch {
      showToast('Copy failed', 'error')
    }
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
            <input type="checkbox" checked={enhance} onChange={(e) => setEnhance(e.target.checked)} />
            <span>
              Enhance
              {serverEnhancerOff && (
                <span
                  className="ml-2 text-xs text-neutral-400 align-middle"
                  title="Backend enhancer is disabled (ENHANCER_ENABLED=false). Toggle has no effect."
                >
                  (server off)
                </span>
              )}
            </span>
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={forceJson} onChange={(e) => setForceJson(e.target.checked)} /> Force JSON
          </label>
          <button onClick={() => setSettingsOpen(true)} className="bg-neutral-800 hover:bg-neutral-700 px-3 py-2 rounded">
            Settings
          </button>
          <button onClick={() => setStatsOpen(true)} className="bg-neutral-800 hover:bg-neutral-700 px-3 py-2 rounded">
            Stats
          </button>
          <button onClick={onGenerate} className="ml-auto bg-green-700 hover:bg-green-600 px-4 py-2 rounded disabled:opacity-50" disabled={loading}>
            {loading ? 'Generating...' : 'Generate'}
          </button>
        </div>

        <Console value={raw} onChange={setRaw} onSubmit={onGenerate} tokenCostPerK={tokenCostPerK} />
        <OutputPanel result={result} onLike={onLike} onCopy={onCopy} tokenCostPerK={tokenCostPerK} />
        <HistoryList defaultWithText={storeText} />
      </div>

      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        storeText={storeText}
        onToggleStoreText={setStoreText}
        tokenCostPerK={tokenCostPerK}
        onUpdateTokenCostPerK={setTokenCostPerK}
      />
      <StatsPanel open={statsOpen} onClose={() => setStatsOpen(false)} />
    </div>
  )
}

