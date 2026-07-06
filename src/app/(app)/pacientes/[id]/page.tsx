import { createClient } from '@/lib/supabase/server'
import { revalidatePath } from 'next/cache'
import { notFound } from 'next/navigation'
import CopyButton from '@/components/CopyButton'

export const dynamic = 'force-dynamic'

async function cambiarEstado(formData: FormData) {
  'use server'
  const supabase = await createClient()
  await supabase.from('patients')
    .update({ status: String(formData.get('status')) })
    .eq('id', String(formData.get('patient_id')))
  revalidatePath('/pacientes'); revalidatePath('/dashboard')
}

async function asignarProtocolo(formData: FormData) {
  'use server'
  const supabase = await createClient()
  const protocolId = String(formData.get('protocol_id') || '')
  const patientId = String(formData.get('patient_id'))
  if (!protocolId) return
  const { data: proto } = await supabase.from('protocols')
    .select('steps').eq('id', protocolId).single()
  await supabase.from('patient_protocols').insert({
    patient_id: patientId,
    protocol_id: protocolId,
    progress: proto?.steps ?? [],   // copia viva: el avance es por paciente
  })
  revalidatePath(`/pacientes/${patientId}`)
}

async function togglePaso(formData: FormData) {
  'use server'
  const supabase = await createClient()
  const ppId = String(formData.get('pp_id'))
  const idx = Number(formData.get('idx'))
  const patientId = String(formData.get('patient_id'))
  const { data: pp } = await supabase.from('patient_protocols')
    .select('progress').eq('id', ppId).single()
  const progress = [...((pp?.progress as any[]) ?? [])]
  if (progress[idx]) progress[idx] = { ...progress[idx], done: !progress[idx].done }
  await supabase.from('patient_protocols').update({ progress }).eq('id', ppId)
  revalidatePath(`/pacientes/${patientId}`)
}

export default async function PacientePage(props: any) {
  const { id } = await props.params
  const supabase = await createClient()

  const { data: p } = await supabase.from('patients')
    .select('id, full_name, email, status, access_token').eq('id', id).single()
  if (!p) return notFound()

  const { data: pp } = await supabase.from('patient_protocols')
    .select('id, progress, protocols(title)')
    .eq('patient_id', p.id).order('assigned_at', { ascending: false }).limit(1).maybeSingle()

  const { data: protocolos } = await supabase.from('protocols')
    .select('id, title').order('created_at', { ascending: false })

  const portalUrl = `${process.env.NEXT_PUBLIC_APP_URL ?? ''}/portal/${p.access_token}`
  const progress: any[] = (pp?.progress as any[]) ?? []
  const hechos = progress.filter(s => s.done).length

  return (
    <div style={{ maxWidth: 620 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <div style={{ fontSize: 19, fontWeight: 600 }}>{p.full_name}</div>
        <form action={cambiarEstado} style={{ display: 'flex', gap: 8 }}>
          <input type="hidden" name="patient_id" value={p.id} />
          <select name="status" defaultValue={p.status} style={sel}>
            <option value="onboarding">Onboarding</option>
            <option value="activo">Activo</option>
            <option value="pausado">Pausado</option>
          </select>
          <button type="submit" style={btnSm}>Guardar</button>
        </form>
      </div>
      <div style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 22 }}>{p.email || 'Sin email'}</div>

      {/* Portal */}
      <section style={{ background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 12, padding: 16, marginBottom: 18 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Su portal privado</div>
        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12, lineHeight: 1.5 }}>
          Compártele este link por WhatsApp: ve su protocolo y sus citas, con tu marca.
          El link es su llave — no necesita registrarse.
        </p>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <CopyButton text={portalUrl} label="Copiar link del portal" />
          <a href={`/portal/${p.access_token}`} target="_blank"
            style={{ fontSize: 12, color: 'var(--green-l)', textDecoration: 'none' }}>Verlo como él ↗</a>
        </div>
      </section>

      {/* Protocolo */}
      <section style={{ background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>
          Su protocolo {pp && <span style={{ color: 'var(--muted)', fontWeight: 400 }}>· {hechos}/{progress.length} pasos</span>}
        </div>

        {!pp ? (
          <form action={asignarProtocolo} style={{ display: 'flex', gap: 8 }}>
            <input type="hidden" name="patient_id" value={p.id} />
            <select name="protocol_id" required defaultValue="" style={{ ...sel, flex: 1 }}>
              <option value="" disabled>Elige un protocolo…</option>
              {(protocolos ?? []).map(pr => <option key={pr.id} value={pr.id}>{pr.title}</option>)}
            </select>
            <button type="submit" style={btnSm}>Asignar</button>
          </form>
        ) : (
          <div>
            <div style={{ fontSize: 13, color: 'var(--green-l)', marginBottom: 10 }}>{(pp as any).protocols?.title}</div>
            <div style={{ display: 'grid', gap: 4 }}>
              {progress.map((s: any, i: number) => (
                <form key={i} action={togglePaso} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <input type="hidden" name="pp_id" value={pp.id} />
                  <input type="hidden" name="idx" value={i} />
                  <input type="hidden" name="patient_id" value={p.id} />
                  <button type="submit" title={s.done ? 'Desmarcar' : 'Marcar hecho'}
                    style={{ width: 20, height: 20, borderRadius: '50%', border: '2px solid var(--green)', background: s.done ? 'var(--green)' : 'transparent', color: '#fff', fontSize: 11, cursor: 'pointer', flexShrink: 0 }}>
                    {s.done ? '✓' : ''}
                  </button>
                  <span style={{ fontSize: 13, color: s.done ? 'var(--muted)' : 'var(--txt)', padding: '6px 0' }}>{s.label}</span>
                </form>
              ))}
              {progress.length === 0 && <p style={{ fontSize: 12, color: 'var(--muted)' }}>Este protocolo no tiene pasos cargados.</p>}
            </div>
            <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 10 }}>
              Cada paso que marcas, el paciente lo ve reflejado en su portal al instante.
            </p>
          </div>
        )}
      </section>
    </div>
  )
}

const sel: React.CSSProperties = { background: 'var(--panel)', border: '1px solid var(--line)', color: 'var(--txt)', padding: '8px 10px', borderRadius: 8, fontSize: 13, fontFamily: 'inherit' }
const btnSm: React.CSSProperties = { background: 'var(--green)', color: '#fff', border: 'none', padding: '8px 14px', borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: 'pointer' }
