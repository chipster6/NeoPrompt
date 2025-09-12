import React from 'react'

type Props = {
  result: any
  onLike: (like: boolean) => void
}

export default function OutputPanel({ result, onLike }: Props) {
  if (!result) return null
  return (
    <div className="bg-neutral-950 p-3 rounded border border-green-900">
      <div className="text-xs text-green-400 mb-2 flex gap-2 items-center">
        <span>Recipe: {result.recipe_id}</span>
        <span>Ops: {result.operators.join(', ')}</span>
        <span>Propensity: {result.propensity.toFixed(2)}</span>
      </div>
      <pre className="whitespace-pre-wrap text-green-200">{result.engineered_prompt}</pre>
      <div className="mt-3 flex gap-2">
        <button className="bg-green-700 hover:bg-green-600 px-3 py-1 rounded" onClick={() => navigator.clipboard.writeText(result.engineered_prompt)}>
          Copy
        </button>
        <button className="bg-green-700/50 hover:bg-green-600/60 px-3 py-1 rounded" onClick={() => onLike(true)}>
          👍
        </button>
        <button className="bg-green-700/50 hover:bg-green-600/60 px-3 py-1 rounded" onClick={() => onLike(false)}>
          👎
        </button>
      </div>
    </div>
  )
}

