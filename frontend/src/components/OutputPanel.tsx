import React from 'react'
import TokenEstimate from './TokenEstimate'

type Props = {
  result: any
  onLike: (like: boolean) => void
  onCopy: (text: string) => void
  tokenCostPerK?: number
}

export default function OutputPanel({ result, onLike, onCopy, tokenCostPerK }: Props) {
  if (!result) return null
  return (
    <div className="bg-neutral-950 p-3 rounded border border-green-900">
      <div className="text-xs text-green-400 mb-2 flex gap-3 items-center flex-wrap">
        <span>Recipe: {result.recipe_id}</span>
        {Array.isArray(result.operators) && <span>Ops: {result.operators.join(', ')}</span>}
        {typeof result.propensity === 'number' && (
          <span>Propensity: {Number(result.propensity).toFixed(2)}</span>
        )}
        {typeof result.engineered_prompt === 'string' && (
          <TokenEstimate text={result.engineered_prompt} label="Output tokens" costPerK={tokenCostPerK} />
        )}
      </div>
      <pre className="whitespace-pre-wrap text-green-200" aria-label="Engineered prompt output">
        {result.engineered_prompt}
      </pre>
      <div className="mt-3 flex gap-2">
        <button
          className="bg-green-700 hover:bg-green-600 px-3 py-1 rounded"
          aria-label="Copy engineered prompt"
          title="Copy engineered prompt"
          onClick={() => onCopy(result.engineered_prompt)}
        >
          Copy
        </button>
        <button
          className="bg-green-700/50 hover:bg-green-600/60 px-3 py-1 rounded"
          aria-label="Thumbs up"
          title="Mark as helpful"
          onClick={() => onLike(true)}
        >
          👍
        </button>
        <button
          className="bg-green-700/50 hover:bg-green-600/60 px-3 py-1 rounded"
          aria-label="Thumbs down"
          title="Mark as not helpful"
          onClick={() => onLike(false)}
        >
          👎
        </button>
      </div>
    </div>
  )
}

