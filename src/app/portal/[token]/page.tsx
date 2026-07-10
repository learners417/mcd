import { createAdminClient } from '@/lib/supabase/server'
import { notFound } from 'next/navigation'

export const dynamic = 'force-dynamic'

// props: any + await props.params → compatible con Next 14 (objeto plano)
// y Next 15 (Promise). await sobre un no-Promise devuelve el valor: seguro en ambos.
export default async function PortalPage(props: any) {
  const { token } = await props.params
  const admin = createAdminClient()  // service role, solo server-side

  // Paciente por token
  const { data: patient } = await admin.from('patients')
    .select('id, full_name, practitioner_id, ghl_contact_id')
    .eq('access_token', token).single()
  if (!patient) return notFound()

  // Marca del sanador
  const { data: pract } = await admin.from('practitioners')
    .select('brand_name, specialty, brand_color').eq('id', patient.practitioner_id).single()

  // Protocolo asignado (el más reciente)
  const { data: pp } = await admin.from('patient_protocols')
    .select('progress, protocols(title, description, steps)')
    .eq('patient_id', patient.id).order('assigned_at', { ascending: false }).limit(1).maybeSingle()

  // Próxima cita: LA AGENDA REAL (cache GHL), filtrada por el contacto del
  // paciente. Si el paciente aún no está mapeado a GHL, la sección no aparece.
  let sess: any = null
  if (patient.ghl_contact_id) {
    const { data: cacheRow } = await admin.from('ghl_cache')
      .select('payload')
      .eq('practitioner_id', patient.practitioner_id)
      .eq('resource', 'appointments').maybeSingle()
    const ahora = Date.now()
    sess = ((cacheRow?.payload as any[]) ?? [])
      .filter(c => c.contactId === patient.ghl_contact_id
        && ['agendada', 'confirmada'].includes(c.estado)
        && new Date(c.inicio).getTime() >= ahora)
      .sort((a, b) => new Date(a.inicio).getTime() - new Date(b.inicio).getTime())[0] ?? null
  }

  const brand = (pract?.brand_color as string) || '#3D6B4F'
  const proto: any = pp?.protocols
  const steps: any[] = proto?.steps || []
  const ini = (pract?.brand_name || 'S').split(' ').map((w: string) => w[0]).slice(0, 2).join('').toUpperCase()

  return (
    <div style={{ minHeight: '100vh', background: '#050505', display: 'grid', placeItems: 'center', padding: 20 }}>
      <div style={{ maxWidth: 560, width: '100%', background: '#fbfbf8', color: '#1a1a1a', borderRadius: 20, overflow: 'hidden', border: '1px solid #e8ebe8', boxShadow: '0 4px 24px rgba(26,31,28,.08)' }}>
        <div style={{ background: `linear-gradient(135deg, ${shade(brand)}, ${brand})`, padding: '26px 26px 22px', color: '#fff' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <div style={{ width: 38, height: 38, borderRadius: 10, background: 'rgba(255,255,255,.18)', display: 'grid', placeItems: 'center', fontWeight: 700 }}>{ini}</div>
            <div><b style={{ fontSize: 16 }}>{pract?.brand_name || 'Tu profesional'}</b><small style={{ display: 'block', opacity: .8 }}>{pract?.specialty || ''}</small></div>
          </div>
          <div style={{ fontSize: 20, fontWeight: 600 }}>Hola, {patient.full_name.split(' ')[0]} 👋
            <small style={{ display: 'block', fontSize: 13, fontWeight: 400, opacity: .85, marginTop: 2 }}>Este es tu espacio de tratamiento.</small>
          </div>
        </div>

        <div style={{ padding: '24px 26px' }}>
          <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '.05em', color: '#8a8a80', marginBottom: 10, fontWeight: 600 }}>Tu protocolo</div>
          {proto ? (
            <div style={{ background: '#fff', border: '1px solid #eaeae4', borderRadius: 12, padding: 16 }}>
              <h4 style={{ fontSize: 15, marginBottom: 6 }}>{proto.title}</h4>
              {proto.description && <p style={{ fontSize: 13, color: '#555' }}>{proto.description}</p>}
              {steps.length > 0 && (() => {
                const done = steps.filter((s: any) => s.done).length
                const pct = Math.round((done / steps.length) * 100)
                return (
                  <div style={{ margin: '12px 0 4px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#888', marginBottom: 4 }}>
                      <span>Tu avance</span><span>{done} de {steps.length}</span>
                    </div>
                    <div style={{ height: 6, background: '#eee', borderRadius: 3, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: pct + '%', background: brand, transition: 'width .3s' }} />
                    </div>
                  </div>
                )
              })()}
              <ul style={{ listStyle: 'none', marginTop: 8, padding: 0 }}>
                {steps.map((s, i) => (
                  <li key={i} style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '9px 0', fontSize: 13, borderTop: '1px solid #f0f0ec', color: s.done ? '#888' : '#1a1a1a' }}>
                    <span style={{ width: 18, height: 18, borderRadius: '50%', border: `2px solid ${brand}`, background: s.done ? brand : 'transparent', color: '#fff', display: 'grid', placeItems: 'center', fontSize: 10 }}>{s.done ? '✓' : ''}</span>
                    {s.label}
                  </li>
                ))}
              </ul>
            </div>
          ) : <p style={{ fontSize: 13, color: '#888' }}>Tu profesional aún no cargó tu protocolo.</p>}

          {sess && (
            <div style={{ marginTop: 22 }}>
              <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '.05em', color: '#8a8a80', marginBottom: 10, fontWeight: 600 }}>Tu próxima sesión</div>
              <div style={{ background: '#fff', border: '1px solid #eaeae4', borderRadius: 10, padding: '12px 14px', fontSize: 13 }}>
                <b>{new Date(sess.inicio).toLocaleString('es')}</b> · {sess.titulo}
              </div>
            </div>
          )}
        </div>
        <div style={{ fontSize: 11, color: '#a0a098', textAlign: 'center', padding: 14, borderTop: '1px solid #eee' }}>
          Espacio privado de {pract?.brand_name || 'tu profesional'} · powered by MiClínica Digital
        </div>
      </div>
    </div>
  )
}

// oscurece un hex para el gradiente
function shade(hex: string) {
  try {
    const n = parseInt(hex.slice(1), 16)
    const r = Math.max(0, (n >> 16) - 20), g = Math.max(0, ((n >> 8) & 255) - 20), b = Math.max(0, (n & 255) - 20)
    return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')}`
  } catch { return hex }
}
