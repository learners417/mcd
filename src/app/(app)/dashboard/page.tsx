import { createClient } from '@/lib/supabase/server'
import MetricCard from '@/components/MetricCard'

export const dynamic = 'force-dynamic'

// NOTA AUDITORÍA: este dashboard ya lee las fuentes de verdad reales —
// cobros (con comprobante) y la agenda de GHL (via ghl_cache). Las tablas
// payments/sessions del Bloque 0 quedaron obsoletas.
// En el Bloque 2 esta pantalla evoluciona a "Hoy" (la bandeja diaria).
export default async function DashboardPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  const { data: me } = await supabase.from('practitioners')
    .select('brand_name, full_name').eq('id', user?.id).single()
  const name = me?.brand_name || me?.full_name || 'Sanador'

  // Los 6 números, calculados en la base (vista mis_numeros)
  const { data: n } = await supabase.from('mis_numeros')
    .select('*').eq('practitioner_id', user?.id).single()

  // Próximas citas: la agenda REAL (cache de GHL)
  const { data: apptCache } = await supabase.from('ghl_cache')
    .select('payload, fetched_at')
    .eq('practitioner_id', user?.id).eq('resource', 'appointments').single()

  const ahora = Date.now()
  const proximas = ((apptCache?.payload as any[]) ?? [])
    .filter(c => ['agendada', 'confirmada'].includes(c.estado) && new Date(c.inicio).getTime() >= ahora)
    .sort((a, b) => new Date(a.inicio).getTime() - new Date(b.inicio).getTime())
    .slice(0, 5)

  return (
    <div>
      <div style={{ fontSize: 19, fontWeight: 600 }}>
        Hola, <span style={{ color: 'var(--gold)' }}>{name}</span>
      </div>
      <div style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 24 }}>
        Este es el estado de tu práctica hoy.
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 14, marginBottom: 14 }}>
        <MetricCard label="Conversaciones esperando" value={String(n?.conversaciones_esperando ?? 0)} foot="respondelas hoy" tone="gold" />
        <MetricCard label="Citas de hoy" value={String(n?.citas_hoy ?? 0)} />
        <MetricCard label="Personas nuevas" value={String(n?.personas_nuevas_semana ?? 0)} foot="esta semana" />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 14, marginBottom: 28 }}>
        <MetricCard label="Pacientes activos" value={String(n?.pacientes_activos ?? 0)} tone="green" />
        <MetricCard label="Ingresos del mes" value={`$${Number(n?.ingresos_mes ?? 0).toLocaleString('es')}`} foot="USD · con comprobante" tone="gold" />
        <MetricCard label="Cobros verificados" value={String(n?.cobros_totales ?? 0)} foot="tu X/10" />
      </div>

      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Próximas citas</div>
      {proximas.length === 0 ? (
        <p style={{ color: 'var(--muted)', fontSize: 13 }}>
          Sin citas próximas en tu agenda{apptCache ? '' : ' (aún no sincronizaste tu calendario)'}.
        </p>
      ) : (
        <div style={{ display: 'grid', gap: 8 }}>
          {proximas.map((c: any) => (
            <div key={c.id} style={{ display: 'flex', justifyContent: 'space-between', background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 10, padding: '12px 14px', fontSize: 13 }}>
              <span>{c.titulo}</span>
              <span style={{ color: 'var(--muted)' }}>{new Date(c.inicio).toLocaleString('es')}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
