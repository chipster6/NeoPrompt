import React from 'react'

type Props = {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
}

export default function Console({ value, onChange, onSubmit }: Props) {
  return (
    <div className="bg-neutral-950 p-3 rounded border border-green-900">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Type or paste your raw request..."
        className="w-full h-40 bg-neutral-950 outline-none"
      />
      <div className="text-xs text-green-500 mt-2">Ctrl/⌘+Enter to generate</div>
    </div>
  )
}

