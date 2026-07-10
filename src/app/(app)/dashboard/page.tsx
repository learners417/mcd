import Link from 'next/link'
import { createClient } from '@/lib/supabase/server'
import { ensureFresh, getConnection } from '@/lib/ghl/sync'
import MetricCard from '@/components/MetricCard'
import SyncButton from '@/components/SyncButton'

export const dynamic = 'force-dynamic'

export default async function HoyPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (user) await ensureFresh(user.id)

  const { data: me } = await supabase.from('practitioners').select('brand_name, full_name').eq('id', user?.id).single()
  const name = (me?.brand_name || me?.full_name || 'Hola').split(' ').slice(0, 2).join(' ')

  const { data: n } = await supabase.from('mis_numeros').select('*').eq('practitioner_id', user?.id).single()
  const conn = user ? await getConnection(user.id) : null
  const conectado = Boolean(conn?.private_token)

  const { data: convCache } = await supabase.from('ghl_cache').select('payload').eq('practitioner_id', user?.id).eq('resource', 'conversations').maybeSingle()
  const esperando = ((convCache?.payload as any[]) ?? []).filter(c => c.sinLeer > 0)
    .sort((a, b) => +new Date(b.fecha) - +new Date(a.fecha)).slice(0, 5)

  const { data: apptCache } = await supabase.from('ghl_cache').select('payload, fetched_at').eq('practitioner_id', user?.id).eq('resource', 'appointments').maybeSingle()
  const finDeHoy = new Date(); finDeHoy.setHours(23, 59, 59, 999)
  const citasHoy = ((apptCache?.payload as any[]) ?? [])
    .filter(c => ['agendada', 'confirmada'].includes(c.estado) && new Date(c.inicio) >= new Date(Date.now() - 3600000) && new Date(c.inicio) <= finDeHoy)
    .sort((a, b) => +new Date(a.inicio) - +new Date(b.inicio))

  const sinPacientes = (n?.pacientes_activos ?? 0) === 0

  return (
    <div style={{ maxWidth: 900 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="mcd-h1">Buen día, <b>{name}</b></h1>
          <p className="mcd-sub" style={{ marginTop: 4 }}>Esto es lo que tu práctica necesita de ti hoy.</p>
        </div>
        {conectado && <SyncButton lastSync={apptCache?.fetched_at ?? null} />}
      </div>

      <div style={{ height: 30 }} />

      {/* conversaciones esperando */}
      {esperando.length > 0 && (
        <section>
          <div className="mcd-section">{esperando.length === 1 ? '1 persona espera tu respuesta' : `${esperando.length} personas esperan tu respuesta`}</div>
          {esperando.map((c: any) => (
            <Link key={c.id} href={`/conversaciones/${c.id}?nombre=${encodeURIComponent(c.nombre)}&contactId=${c.contactId ?? ''}`}
              className="mcd-row mcd-accent-gold" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 9, textDecoration: 'none', color: 'var(--ink)' }}>
              <span style={{ minWidth: 0, paddingLeft: 4 }}>
                <span style={{ fontWeight: 600, fontSize: 14, display: 'block' }}>{c.nombre}</span>
                <span style={{ color: 'var(--muted)', fontSize: 13, display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 440 }}>{c.ultimoMensaje || 'Nuevo mensaje'}</span>
              </span>
              <span style={{ color: 'var(--gold)', fontSize: 12, fontWeight: 500, flexShrink: 0, marginLeft: 12 }}>{c.sinLeer} sin leer · responder →</span>
            </Link>
          ))}
          <p className="mcd-faint" style={{ fontSize: 12, margin: '8px 2px 0' }}>Respóndeles desde tu WhatsApp. Cada hora sin respuesta enfría la conversación.</p>
        </section>
      )}

      {esperando.length > 0 && <hr className="mcd-divider" />}

      {/* tu día */}
      <section>
        <div className="mcd-section">Tu día</div>
        {citasHoy.length === 0 ? (
          <div className="mcd-empty">Sin citas para hoy{conectado ? '.' : ' — tu agenda se conecta desde Mi marca.'}</div>
        ) : citasHoy.map((c: any) => (
          <div key={c.id} className="mcd-row mcd-accent-green" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 9 }}>
            <span style={{ fontSize: 14, fontWeight: 500, paddingLeft: 4 }}>{c.titulo}</span>
            <span style={{ fontSize: 15, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{new Date(c.inicio).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })}</span>
          </div>
        ))}
      </section>

      {/* primer día */}
      {sinPacientes && (
        <>
          <hr className="mcd-divider" />
          <section className="mcd-card" style={{ padding: 24, background: 'linear-gradient(135deg,var(--green-tint),var(--green-bg))', border: '1px solid #DCE8E0' }}>
            <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 6 }}>Tu primer paso: ordena tu práctica actual</div>
            <p style={{ fontSize: 14, color: 'var(--muted)', lineHeight: 1.6, marginBottom: 16 }}>Carga hoy los pacientes que ya tienes. A cada uno le asignas su protocolo y le compartes su portal privado con tu marca. Desde ese momento, tu práctica vive en un solo lugar.</p>
            <Link href="/pacientes" className="mcd-btn" style={{ textDecoration: 'none', display: 'inline-block' }}>Cargar mis pacientes →</Link>
          </section>
        </>
      )}

      <hr className="mcd-divider" />

      {/* los 6 números */}
      <section>
        <div className="mcd-section">Tus números</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 14 }}>
          <MetricCard icon="✦" label="Personas nuevas" value={String(n?.personas_nuevas_semana ?? 0)} foot="esta semana" />
          <MetricCard icon="💬" label="Conversaciones" value={String(n?.conversaciones_esperando ?? 0)} foot="esperando respuesta" tone="gold" />
          <MetricCard icon="📅" label="Citas de hoy" value={String(n?.citas_hoy ?? 0)} foot="agendadas" />
          <MetricCard icon="👥" label="Pacientes activos" value={String(n?.pacientes_activos ?? 0)} foot="en tratamiento" tone="green" />
          <MetricCard icon="💰" label="Ingresos del mes" value={`$${Number(n?.ingresos_mes ?? 0).toLocaleString('es')}`} foot="USD verificados" tone="gold" />
          <MetricCard icon="🥋" label="Cobros verificados" value={String(n?.cobros_totales ?? 0)} foot="tu camino al 10" tone="green" />
        </div>
      </section>

      {/* ROI */}
      {Number(n?.roi_mes ?? 0) > 0 ? (
        <div style={{ marginTop: 22, background: 'linear-gradient(135deg,var(--green-tint),var(--green-bg))', border: '1px solid #DCE8E0', borderRadius: 'var(--r)', padding: '22px 24px', display: 'flex', alignItems: 'center', gap: 16 }}>
          <div style={{ width: 44, height: 44, borderRadius: 13, background: 'var(--card)', display: 'grid', placeItems: 'center', fontSize: 20, boxShadow: 'var(--shadow)', flexShrink: 0 }}>📈</div>
          <div style={{ fontSize: 15, lineHeight: 1.5 }}>Este mes tu sistema facturó <b style={{ color: 'var(--gold)' }}>${Number(n?.ingresos_mes ?? 0).toLocaleString('es')} USD</b>. Tu inversión en MiClínica se pagó <b style={{ color: 'var(--green)' }}>{n?.roi_mes}×</b>.</div>
        </div>
      ) : Number(n?.ingresos_mes ?? 0) > 0 ? (
        <div style={{ marginTop: 22, background: 'var(--green-tint)', border: '1px solid #DCE8E0', borderRadius: 'var(--r)', padding: '18px 22px', fontSize: 15 }}>
          Este mes tu sistema facturó <b style={{ color: 'var(--gold)' }}>${Number(n?.ingresos_mes ?? 0).toLocaleString('es')} USD</b>.
        </div>
      ) : null}
    </div>
  )
}
