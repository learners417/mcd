'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function CobroForm({ patients }: { patients: { id: string; full_name: string }[] }) {
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const router = useRouter()

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setBusy(true); setMsg('')
    const form = new FormData(e.currentTarget)
    const res = await fetch('/api/cobros', { method: 'POST', body: form })
    const data = await res.json()
    setBusy(false)
    if (!res.ok) { setMsg(data.error || 'No se pudo registrar'); return }
    setMsg('✓ Cobro registrado con su comprobante')
    ;(e.target as HTMLFormElement).reset()
    router.refresh()
  }

  return (
    <form onSubmit={submit} style={{ display: 'grid', gap: 8, maxWidth: 440, marginBottom: 28 }}>
      <input name="amount_usd" type="number" step="0.01" min="1" required placeholder="Monto en USD" style={inp} />
      <input name="concept" placeholder="Concepto (ej: Programa 12 semanas)" style={inp} />
      <select name="patient_id" style={inp} defaultValue="">
        <option value="">— Sin paciente asociado —</option>
        {patients.map(p => <option key={p.id} value={p.id}>{p.full_name}</option>)}
      </select>
      <label style={{ fontSize: 12, color: 'var(--muted)' }}>
        Comprobante (obligatorio — captura de la transferencia o recibo)
        <input name="receipt" type="file" accept="image/*,.pdf" required
          style={{ ...inp, marginTop: 6, width: '100%', padding: 10 }} />
      </label>
      <button type="submit" disabled={busy} style={{ ...btn, opacity: busy ? .6 : 1 }}>
        {busy ? 'Registrando…' : 'Registrar cobro'}
      </button>
      {msg && <div style={{ fontSize: 13, color: msg.startsWith('✓') ? 'var(--green-l)' : '#e06666' }}>{msg}</div>}
    </form>
  )
}

const inp: React.CSSProperties = { background: 'var(--panel)', border: '1px solid var(--line)', color: 'var(--txt)', padding: '10px 12px', borderRadius: 9, fontSize: 14, fontFamily: 'inherit' }
const btn: React.CSSProperties = { background: 'var(--green)', color: '#fff', border: 'none', padding: '10px 18px', borderRadius: 9, fontSize: 14, fontWeight: 500, cursor: 'pointer', justifySelf: 'start' }
