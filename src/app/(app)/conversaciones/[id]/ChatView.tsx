'use client'
import { useEffect, useRef, useState } from 'react'

type Mensaje = { id: string; texto: string; entrante: boolean; fecha: string; canal: string }

export default function ChatView({ conversationId, contactId, nombre }: {
  conversationId: string; contactId: string; nombre: string
}) {
  const [mensajes, setMensajes] = useState<Mensaje[]>([])
  const [texto, setTexto] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [cargando, setCargando] = useState(true)
  const [err, setErr] = useState('')
  const [iaLoading, setIaLoading] = useState('')
  const [sugerencia, setSugerencia] = useState('')
  const finRef = useRef<HTMLDivElement>(null)

  function historialTexto() {
    return mensajes.map(m => `${m.entrante ? 'Persona' : 'Yo'}: ${m.texto}`).join('\n')
  }

  async function ia(tarea: string, intencion?: string) {
    setIaLoading(tarea); setSugerencia('')
    try {
      const res = await fetch('/api/ai/asistente', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tarea, historial: historialTexto(), conversationId, intencion }),
      })
      const data = await res.json()
      if (res.ok) {
        if (tarea === 'redactar') setTexto(data.resultado)
        else setSugerencia(data.resultado)
      } else setErr(data.error || 'La IA no respondió')
    } catch { setErr('Error con la IA') }
    setIaLoading('')
  }

  async function cargar() {
    try {
      const res = await fetch(`/api/ghl/mensajes?conversationId=${conversationId}`)
      const data = await res.json()
      if (res.ok) setMensajes((data.mensajes ?? []).slice().reverse())
    } catch {}
    setCargando(false)
  }

  useEffect(() => {
    cargar()
    const t = setInterval(() => { if (document.visibilityState === 'visible') cargar() }, 15000)
    return () => clearInterval(t)
  }, [conversationId])
  useEffect(() => { finRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [mensajes.length])

  async function enviar() {
    if (!texto.trim() || enviando) return
    setEnviando(true); setErr('')
    const optimista: Mensaje = { id: 'tmp-' + Date.now(), texto: texto.trim(), entrante: false, fecha: new Date().toISOString(), canal: 'WhatsApp' }
    setMensajes(m => [...m, optimista]); const t = texto.trim(); setTexto('')
    try {
      const res = await fetch('/api/ghl/mensajes', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contactId, text: t }),
      })
      const data = await res.json()
      if (!res.ok) { setErr(data.error || 'No se pudo enviar'); setMensajes(m => m.filter(x => x.id !== optimista.id)); setTexto(t) }
      else setTimeout(cargar, 1200)
    } catch {
      setErr('Error de red'); setMensajes(m => m.filter(x => x.id !== optimista.id)); setTexto(t)
    }
    setEnviando(false)
  }

  return (
    <div style={{ maxWidth: 640, height: 'calc(100vh - 120px)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ fontSize: 17, fontWeight: 600, marginBottom: 4 }}>{nombre}</div>
      <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 16 }}>WhatsApp · respondes desde aquí, sin salir de MiClínica</div>

      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8, padding: '4px 2px' }}>
        {cargando ? <p style={{ color: 'var(--muted)', fontSize: 13 }}>Cargando conversación…</p>
          : mensajes.length === 0 ? <p style={{ color: 'var(--muted)', fontSize: 13 }}>Sin mensajes todavía.</p>
          : mensajes.map(m => (
            <div key={m.id} style={{ alignSelf: m.entrante ? 'flex-start' : 'flex-end', maxWidth: '75%', background: m.entrante ? 'var(--card)' : 'var(--green)', color: m.entrante ? 'var(--ink)' : '#fff', border: m.entrante ? '1px solid var(--line)' : 'none', borderRadius: 12, padding: '9px 13px', fontSize: 13 }}>
              {m.texto}
              <div style={{ fontSize: 10, opacity: .6, marginTop: 3, textAlign: 'right' }}>
                {new Date(m.fecha).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          ))}
        <div ref={finRef} />
      </div>

      {sugerencia && (
        <div style={{ background: 'var(--green-tint)', border: '1px solid var(--green)', borderRadius: 10, padding: '10px 12px', fontSize: 12, marginTop: 10, color: 'var(--ink)' }}>
          <b style={{ color: 'var(--green-l)' }}>✨ Asistente:</b> {sugerencia}
        </div>
      )}

      <div style={{ display: 'flex', gap: 6, marginTop: 12, flexWrap: 'wrap' }}>
        <button onClick={() => ia('redactar', 'Responder de forma natural para avanzar la conversación')} disabled={!!iaLoading}
          style={iaBtn}>{iaLoading === 'redactar' ? '…' : '✨ Redactar respuesta'}</button>
        <button onClick={() => ia('resumir')} disabled={!!iaLoading} style={iaBtn}>{iaLoading === 'resumir' ? '…' : 'Resumir'}</button>
        <button onClick={() => ia('sugerir')} disabled={!!iaLoading} style={iaBtn}>{iaLoading === 'sugerir' ? '…' : 'Próximo paso'}</button>
      </div>

      {err && <div style={{ color: 'var(--danger)', fontSize: 12, margin: '6px 0' }}>{err}</div>}

      <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
        <input value={texto} onChange={e => setTexto(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') enviar() }}
          placeholder="Escribí tu respuesta…"
          style={{ flex: 1, background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--ink)', padding: '11px 14px', borderRadius: 10, fontSize: 14, fontFamily: 'inherit' }} />
        <button onClick={enviar} disabled={enviando || !texto.trim()}
          style={{ background: 'var(--green)', color: '#fff', border: 'none', padding: '11px 20px', borderRadius: 10, fontSize: 14, fontWeight: 500, cursor: 'pointer', opacity: (enviando || !texto.trim()) ? .5 : 1 }}>
          {enviando ? '…' : 'Enviar'}
        </button>
      </div>
    </div>
  )
}

// estilo compartido para los botones del asistente
const iaBtn: React.CSSProperties = { background: 'transparent', border: '1px solid var(--line)', color: 'var(--ink)', padding: '6px 12px', borderRadius: 8, fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }
