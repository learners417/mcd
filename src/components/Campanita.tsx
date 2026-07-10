'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

type Notif = { id: string; tipo: string; titulo: string; cuerpo?: string; link?: string; leida: boolean; created_at: string }

export default function Campanita() {
  const [abierto, setAbierto] = useState(false)
  const [notifs, setNotifs] = useState<Notif[]>([])
  const [sinLeer, setSinLeer] = useState(0)
  const router = useRouter()

  async function cargar() {
    try {
      const res = await fetch('/api/notificaciones')
      const data = await res.json()
      if (res.ok) { setNotifs(data.notificaciones ?? []); setSinLeer(data.sinLeer ?? 0) }
    } catch {}
  }
  useEffect(() => {
    cargar()
    const t = setInterval(() => { if (document.visibilityState === 'visible') cargar() }, 30000)
    const onVis = () => { if (document.visibilityState === 'visible') cargar() }
    document.addEventListener('visibilitychange', onVis)
    return () => { clearInterval(t); document.removeEventListener('visibilitychange', onVis) }
  }, [])

  async function abrir() {
    setAbierto(o => !o)
    if (!abierto && sinLeer > 0) {
      await fetch('/api/notificaciones', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      setSinLeer(0)
    }
  }

  const icono: Record<string, string> = { mensaje: '💬', cita: '📅', cobro: '💰', paciente: '👥', sistema: '🔔' }

  return (
    <div style={{ position: 'relative' }}>
      <button onClick={abrir} style={{ width: 40, height: 40, borderRadius: 12, background: 'var(--card)', border: '1px solid var(--line)', display: 'grid', placeItems: 'center', cursor: 'pointer', fontSize: 16, position: 'relative', boxShadow: 'var(--shadow)' }}>
        🔔
        {sinLeer > 0 && (
          <span style={{ position: 'absolute', top: 6, right: 7, background: 'var(--gold)', color: '#fff', fontSize: 10, fontWeight: 700, borderRadius: 10, minWidth: 16, height: 16, display: 'grid', placeItems: 'center', padding: '0 4px', border: '2px solid var(--card)' }}>
            {sinLeer}
          </span>
        )}
      </button>
      {abierto && (
        <div style={{ position: 'absolute', right: 0, top: 34, width: 320, maxHeight: 400, overflowY: 'auto', background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 14, padding: 8, zIndex: 50, boxShadow: 'var(--shadow-lift)' }}>
          {notifs.length === 0 ? (
            <p style={{ color: 'var(--muted)', fontSize: 13, padding: 16, textAlign: 'center' }}>Sin novedades</p>
          ) : notifs.map(n => (
            <div key={n.id} onClick={() => { if (n.link) { setAbierto(false); router.push(n.link) } }}
              style={{ padding: '10px 12px', borderRadius: 8, cursor: n.link ? 'pointer' : 'default', background: n.leida ? 'transparent' : 'var(--green-tint)', marginBottom: 4 }}>
              <div style={{ fontSize: 13, fontWeight: 500 }}>{icono[n.tipo] ?? '🔔'} {n.titulo}</div>
              {n.cuerpo && <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>{n.cuerpo}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
