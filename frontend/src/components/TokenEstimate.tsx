import React, { useMemo } from 'react'

function estimateTokens(text: string): number {
  if (!text) return 0
  // Very rough heuristic: ~4 chars/token
  const chars = text.trim().length
  return Math.max(0, Math.ceil(chars / 4))
}

function fmtCurrency(n: number): string {
  if (n < 0.01) return `$${n.toFixed(4)}`
  return `$${n.toFixed(2)}`
}

export default function TokenEstimate({
  text,
  label = 'Tokens',
  costPerK,
  showCost = true,
}: {
  text: string
  label?: string
  costPerK?: number // USD per 1K tokens
  showCost?: boolean
}) {
  const tokens = useMemo(() => estimateTokens(text), [text])
  const cost = useMemo(() => {
    if (!showCost || !costPerK || costPerK <= 0) return null
    return (tokens / 1000) * costPerK
  }, [tokens, costPerK, showCost])

  return (
    <span className="text-xs text-green-500" title="Approximate token count and cost (heuristic)">
      {label}: ~{tokens.toLocaleString()}
      {cost !== null && typeof cost === 'number' ? ` • ~${fmtCurrency(cost)}` : ''}
    </span>
  )
}
