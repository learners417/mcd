'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function SyncButton({ lastSync }: { lastSync?: string | null }) {
  const [busy, setBusy] = useState(false)
  const router = useRouter()

  async function sync() {
    setBusy(true)
    try { await fetch('/api/ghl/sync?force=1', { method: 'POST' }) } catch {}
    setBusy(false)
    router.refresh()
  }

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
      {lastSync && (
        <span style={{ fontSize: 11, color: 'var(--muted)' }}>
          Actualizado {new Date(lastSync).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })}
        </span>
      )}
      <button onClick={sync} disabled={busy}
        style={{ background: 'transparent', border: '1px solid var(--line)', color: 'var(--txt)', padding: '7px 14px', borderRadius: 8, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit', opacity: busy ? .6 : 1 }}>
        {busy ? 'Actualizando…' : '↻ Actualizar'}
      </button>
    </span>
  )
}
