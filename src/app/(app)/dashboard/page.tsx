import Link from 'next/link'
import { createClient } from '@/lib/supabase/server'
import { ensureFresh, getConnection } from '@/lib/ghl/sync'
import MetricCard from '@/components/MetricCard'
import SyncButton from '@/components/SyncButton'

export const dynamic = 'force-dynamic'

// HOY: la única pantalla que el sanador necesita mirar cada mañana.
// Motor Orden (D0): pacientes actuales, citas. Motor Dinero (D29): conversaciones.
export default async function HoyPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  // Sync suave: si hay GHL conectado y la cache está vieja, refresca.
  if (user) await ensureFresh(user.id)

  const { data: me } = await supabase.from('practitioners')
    .select('brand_name, full_name').eq('id', user?.id).single()
  const name = (me?.brand_name || me?.full_name || 'Hola').split(' ')[0]

  const { data: n } = await supabase.from('mis_numeros')
    .select('*').eq('practitioner_id', user?.id).single()

  const conn = user ? await getConnection(user.id) : null
  const conectado = Boolean(conn?.private_token)

  // Conversaciones esperando (Motor Dinero)
  const { data: convCache } = await supabase.from('ghl_cache')
    .select('payload').eq('practitioner_id', user?.id).eq('resource', 'conversations').maybeSingle()
  const esperando = ((convCache?.payload as any[]) ?? [])
    .filter(c => c.sinLeer > 0)
    .sort((a, b) => new Date(b.fecha).getTime() - new Date(a.fecha).getTime())
    .slice(0, 5)

  // Citas de hoy y próximas (Motor Orden)
  const { data: apptCache } = await supabase.from('ghl_cache')
    .select('payload, fetched_at').eq('practitioner_id', user?.id).eq('resource', 'appointments').maybeSingle()
  const ahora = new Date()
  const finDeHoy = new Date(); finDeHoy.setHours(23, 59, 59, 999)
  const citasHoy = ((apptCache?.payload as any[]) ?? [])
    .filter(c => ['agendada', 'confirmada'].includes(c.estado)
      && new Date(c.inicio) >= new Date(ahora.getTime() - 60 * 60 * 1000)
      && new Date(c.inicio) <= finDeHoy)
    .sort((a, b) => new Date(a.inicio).getTime() - new Date(b.inicio).getTime())

  const sinPacientes = (n?.pacientes_activos ?? 0) === 0

  return (
    <div style={{ maxWidth: 860 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
        <div style={{ fontSize: 20, fontWeight: 600 }}>
          Hola, <span style={{ color: 'var(--gold)' }}>{name}</span>
        </div>
        {conectado && <SyncButton lastSync={apptCache?.fetched_at ?? null} />}
      </div>
      <div style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 24 }}>
        Esto es lo que tu práctica necesita de ti hoy.
      </div>

      {/* ── LA VENTANA DE HOY ── */}
      {esperando.length > 0 && (
        <section style={{ marginBottom: 22 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>
            💬 {esperando.length === 1 ? '1 persona espera' : `${esperando.length} personas esperan`} tu respuesta
          </div>
          <div style={{ display: 'grid', gap: 8 }}>
            {esperando.map((c: any) => (
              <div key={c.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--panel)', border: '1px solid var(--line)', borderLeft: '3px solid var(--gold)', borderRadius: 10, padding: '12px 14px', fontSize: 13 }}>
                <span style={{ minWidth: 0 }}>
                  <b>{c.nombre}</b>
                  <span style={{ color: 'var(--muted)', display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 480 }}>
                    {c.ultimoMensaje || 'Nuevo mensaje'}
                  </span>
                </span>
                <span style={{ color: 'var(--gold-l)', fontSize: 12, flexShrink: 0, marginLeft: 12 }}>
                  {c.sinLeer} sin leer · {c.canal}
                </span>
              </div>
            ))}
          </div>
          <p style={{ color: 'var(--muted)', fontSize: 12, marginTop: 8 }}>
            Respóndeles desde tu WhatsApp. Cada hora sin respuesta enfría la conversación.
          </p>
        </section>
      )}

      <section style={{ marginBottom: 26 }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>📅 Tu día</div>
        {citasHoy.length === 0 ? (
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>
            Sin citas para hoy{conectado ? '' : ' (tu agenda se conecta desde Mi marca)'}.
          </p>
        ) : (
          <div style={{ display: 'grid', gap: 8 }}>
            {citasHoy.map((c: any) => (
              <div key={c.id} style={{ display: 'flex', justifyContent: 'space-between', background: 'var(--panel)', border: '1px solid var(--line)', borderLeft: '3px solid var(--green-l)', borderRadius: 10, padding: '12px 14px', fontSize: 13 }}>
                <span>{c.titulo}</span>
                <b>{new Date(c.inicio).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })}</b>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── MOTOR ORDEN: primer día ── */}
      {sinPacientes && (
        <section style={{ background: '#0c130f', border: '1px solid var(--green)', borderRadius: 14, padding: 20, marginBottom: 26 }}>
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>🌱 Tu primer paso: ordena tu práctica actual</div>
          <p style={{ fontSize: 13, color: 'var(--muted)', lineHeight: 1.6, marginBottom: 14 }}>
            Carga hoy los pacientes que ya tienes. A cada uno le puedes asignar su protocolo
            y compartirle su portal privado con tu marca. Desde ese momento, tu práctica
            vive en un solo lugar — y tú recuperas tu tiempo.
          </p>
          <Link href="/pacientes" style={{ background: 'var(--green)', color: '#fff', padding: '10px 18px', borderRadius: 9, fontSize: 13, fontWeight: 500, textDecoration: 'none' }}>
            Cargar mis pacientes →
          </Link>
        </section>
      )}

      {/* ── LOS 6 NÚMEROS ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12 }}>
        <MetricCard label="Personas nuevas" value={String(n?.personas_nuevas_semana ?? 0)} foot="esta semana" />
        <MetricCard label="Conversaciones" value={String(n?.conversaciones_esperando ?? 0)} foot="esperando respuesta" tone="gold" />
        <MetricCard label="Citas de hoy" value={String(n?.citas_hoy ?? 0)} />
        <MetricCard label="Pacientes activos" value={String(n?.pacientes_activos ?? 0)} tone="green" />
        <MetricCard label="Ingresos del mes" value={`$${Number(n?.ingresos_mes ?? 0).toLocaleString('es')}`} foot="USD verificados" tone="gold" />
        <MetricCard label="Cobros verificados" value={String(n?.cobros_totales ?? 0)} foot="tu camino al 10" />
      </div>

      {/* ── MOTOR DINERO: aún apagado ── */}
      {conectado && esperando.length === 0 && (n?.personas_nuevas_semana ?? 0) === 0 && (
        <p style={{ color: 'var(--muted)', fontSize: 12, marginTop: 18 }}>
          💡 Cuando tu campaña se encienda (lo verás en El Camino), las personas interesadas
          empezarán a aparecer aquí solas.
        </p>
      )}
    </div>
  )
}
