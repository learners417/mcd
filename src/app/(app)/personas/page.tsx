import { createClient } from '@/lib/supabase/server'
import { ensureFresh, getConnection } from '@/lib/ghl/sync'
import SyncButton from '@/components/SyncButton'

export const dynamic = 'force-dynamic'

const COLUMNAS = [
  { key: 'interesada',  titulo: 'Interesadas',  hint: 'Llegaron por tu campaña' },
  { key: 'conversando', titulo: 'Conversando',  hint: 'En WhatsApp contigo' },
  { key: 'agendada',    titulo: 'Agendadas',    hint: 'Con llamada o cita' },
  { key: 'paciente',    titulo: 'Pacientes',    hint: 'Dijeron que sí' },
] as const

export default async function PersonasPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (user) await ensureFresh(user.id)

  const conn = user ? await getConnection(user.id) : null
  const conectado = Boolean(conn?.private_token)

  const { data: oppCache } = await supabase.from('ghl_cache')
    .select('payload, fetched_at').eq('practitioner_id', user?.id).eq('resource', 'opportunities').maybeSingle()
  const ventas = ((oppCache?.payload as any[]) ?? [])
    .filter(v => v.estadoGhl !== 'lost' && v.estadoGhl !== 'abandoned')

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
        <div style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-.02em' }}>Personas</div>
        {conectado && <SyncButton lastSync={oppCache?.fetched_at ?? null} />}
      </div>
      <div style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 22 }}>
        El recorrido de cada persona interesada hasta convertirse en tu paciente.
      </div>

      {!conectado ? (
        <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 22, fontSize: 13, color: 'var(--muted)', maxWidth: 520, lineHeight: 1.6 }}>
          Este espacio se enciende cuando tu sistema esté conectado — lo hace el equipo
          durante tu primera semana. Cuando tu campaña arranque, cada persona que escriba
          aparecerá aquí sola, con su recorrido a la vista.
        </div>
      ) : ventas.length === 0 ? (
        <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 22, fontSize: 13, color: 'var(--muted)', maxWidth: 520, lineHeight: 1.6 }}>
          Todavía no hay personas en el recorrido. Cuando tu campaña se encienda
          (~día 29 de El Camino), esto se llena solo.
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12 }}>
          {COLUMNAS.map(col => {
            const items = ventas.filter(v => v.etapa === col.key)
            return (
              <div key={col.key} style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 12, minHeight: 200 }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 2 }}>
                  {col.titulo} <span style={{ color: 'var(--muted)', fontWeight: 400 }}>· {items.length}</span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 10 }}>{col.hint}</div>
                <div style={{ display: 'grid', gap: 6 }}>
                  {items.map((v: any) => (
                    <div key={v.id} style={{ background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, padding: '9px 10px', fontSize: 12 }}>
                      <div style={{ fontWeight: 500 }}>{v.nombre}</div>
                      {v.valor > 0 && <div style={{ color: 'var(--gold)', fontSize: 11, marginTop: 2 }}>${v.valor.toLocaleString('es')}</div>}
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
