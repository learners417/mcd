'use client'
import { useState } from 'react'

export default function CopyButton({ text, label = 'Copiar link' }: { text: string; label?: string }) {
  const [ok, setOk] = useState(false)
  async function copy() {
    try { await navigator.clipboard.writeText(text) } catch {
      const ta = document.createElement('textarea')
      ta.value = text; document.body.appendChild(ta); ta.select()
      document.execCommand('copy'); document.body.removeChild(ta)
    }
    setOk(true); setTimeout(() => setOk(false), 1800)
  }
  return (
    <button onClick={copy}
      style={{ background: ok ? 'var(--green)' : 'transparent', border: '1px solid ' + (ok ? 'var(--green)' : 'var(--line)'), color: ok ? '#fff' : 'var(--ink)', padding: '7px 14px', borderRadius: 8, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit', transition: '.15s' }}>
      {ok ? '✓ Copiado' : label}
    </button>
  )
}
