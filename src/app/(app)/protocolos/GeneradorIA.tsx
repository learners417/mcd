'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function GeneradorIA() {
  const [desc, setDesc] = useState('')
  const [busy, setBusy] = useState(false)
  const [preview, setPreview] = useState<any>(null)
  const [err, setErr] = useState('')
  const router = useRouter()

  async function generar() {
    if (!desc.trim()) return
    setBusy(true); setErr(''); setPreview(null)
    try {
      const res = await fetch('/api/ai/asistente', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tarea: 'protocolo', descripcion: desc }),
      })
      const data = await res.json()
      if (res.ok && data.resultado) setPreview(data.resultado)
      else setErr('La IA no pudo generar el protocolo. Probá describirlo distinto.')
    } catch { setErr('Error con la IA') }
    setBusy(false)
  }

  async function guardar() {
    setBusy(true)
    const res = await fetch('/api/protocolos', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(preview),
    })
    setBusy(false)
    if (res.ok) { setPreview(null); setDesc(''); router.refresh() }
    else setErr('No se pudo guardar')
  }

  return (
    <div style={{ background: 'var(--green-tint)', border: '1px solid var(--green)', borderRadius: 12, padding: 16, marginBottom: 22 }}>
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>✨ Generar con IA</div>
      <div style={{ display: 'flex', gap: 8 }}>
        <input value={desc} onChange={e => setDesc(e.target.value)} placeholder="Describí el tratamiento en tus palabras…"
          style={{ flex: 1, background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--ink)', padding: '10px 12px', borderRadius: 9, fontSize: 14, fontFamily: 'inherit' }} />
        <button onClick={generar} disabled={busy || !desc.trim()} style={{ background: 'var(--green)', color: '#fff', border: 'none', padding: '10px 18px', borderRadius: 9, fontSize: 14, fontWeight: 500, cursor: 'pointer', opacity: busy ? .6 : 1 }}>
          {busy ? '…' : 'Generar'}
        </button>
      </div>
      {err && <div style={{ color: 'var(--danger)', fontSize: 12, marginTop: 8 }}>{err}</div>}
      {preview && (
        <div style={{ marginTop: 12, background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 10, padding: 14 }}>
          <div style={{ fontWeight: 600, fontSize: 14 }}>{preview.title}</div>
          <div style={{ fontSize: 12, color: 'var(--muted)', margin: '4px 0 8px' }}>{preview.description}</div>
          <ul style={{ paddingLeft: 18, fontSize: 13, display: 'grid', gap: 3 }}>
            {(preview.steps ?? []).map((s: any, i: number) => <li key={i}>{s.label}</li>)}
          </ul>
          <button onClick={guardar} disabled={busy} style={{ background: 'var(--green)', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: 'pointer', marginTop: 10 }}>Guardar protocolo</button>
        </div>
      )}
    </div>
  )
}
