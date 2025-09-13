import React from 'react'
import TokenEstimate from './TokenEstimate'

type Props = {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  tokenCostPerK?: number
}

export default function Console({ value, onChange, onSubmit, tokenCostPerK }: Props) {
  return (
    <div className="bg-neutral-950 p-3 rounded border border-green-900">
      <textarea
        aria-label="Raw prompt input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
            e.preventDefault()
            onSubmit()
          }
        }}
        placeholder="Type or paste your raw request..."
        className="w-full h-40 bg-neutral-950 outline-none"
      />
      <div className="flex items-center justify-between mt-2">
        <div className="text-xs text-green-500">Ctrl/⌘+Enter to generate</div>
        <TokenEstimate text={value} label="Input tokens" costPerK={tokenCostPerK} />
      </div>
    </div>
  )
}

