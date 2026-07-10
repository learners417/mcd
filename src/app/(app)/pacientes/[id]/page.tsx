import { createClient } from '@/lib/supabase/server'
import { revalidatePath } from 'next/cache'
import { notFound } from 'next/navigation'
import CopyButton from '@/components/CopyButton'

export const dynamic = 'force-dynamic'

async function cambiarEstado(formData: FormData) {
  'use server'
  const supabase = await createClient()
  await supabase.from('patients').update({ status: String(formData.get('status')) }).eq('id', String(formData.get('patient_id')))
  revalidatePath('/pacientes'); revalidatePath('/dashboard')
}

async function asignarProtocolo(formData: FormData) {
  'use server'
  const supabase = await createClient()
  const protocolId = String(formData.get('protocol_id') || '')
  const patientId = String(formData.get('patient_id'))
  if (!protocolId) return
  const { data: proto } = await supabase.from('protocols').select('steps').eq('id', protocolId).single()
  await supabase.from('patient_protocols').insert({ patient_id: patientId, protocol_id: protocolId, progress: proto?.steps ?? [] })
  revalidatePath(`/pacientes/${patientId}`)
}

async function togglePaso(formData: FormData) {
  'use server'
  const supabase = await createClient()
  const ppId = String(formData.get('pp_id')); const idx = Number(formData.get('idx')); const patientId = String(formData.get('patient_id'))
  const { data: pp } = await supabase.from('patient_protocols').select('progress').eq('id', ppId).single()
  const progress = [...((pp?.progress as any[]) ?? [])]
  if (progress[idx]) progress[idx] = { ...progress[idx], done: !progress[idx].done }
  await supabase.from('patient_protocols').update({ progress }).eq('id', ppId)
  revalidatePath(`/pacientes/${patientId}`)
}

async function agregarNota(formData: FormData) {
  'use server'
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  const patientId = String(formData.get('patient_id'))
  const body = String(formData.get('body') || '').trim()
  if (body) await supabase.from('patient_notes').insert({ patient_id: patientId, practitioner_id: user!.id, body })
  revalidatePath(`/pacientes/${patientId}`)
}

export default async function PacientePage(props: any) {
  const { id } = await props.params
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  const { data: p } = await supabase.from('patients')
    .select('id, full_name, email, phone, status, access_token, ghl_contact_id').eq('id', id).single()
  if (!p) return notFound()

  const { data: pp } = await supabase.from('patient_protocols')
    .select('id, progress, protocols(title)').eq('patient_id', p.id).order('assigned_at', { ascending: false }).limit(1).maybeSingle()
  const { data: protocolos } = await supabase.from('protocols').select('id, title').order('created_at', { ascending: false })
  const { data: notas } = await supabase.from('patient_notes')
    .select('id, body, created_at').eq('patient_id', p.id).order('created_at', { ascending: false }).limit(20)

  // ── enriquecimiento GHL (solo lectura desde la cache) ──
  let ghl: { ultimaConv?: string; proximaCita?: string; origen?: string } = {}
  if (p.ghl_contact_id) {
    const { data: convC } = await supabase.from('ghl_cache').select('payload').eq('practitioner_id', user?.id).eq('resource', 'conversations').maybeSingle()
    const conv = ((convC?.payload as any[]) ?? []).find(c => c.contactId === p.ghl_contact_id)
    if (conv) ghl.ultimaConv = conv.ultimoMensaje
    const { data: apptC } = await supabase.from('ghl_cache').select('payload').eq('practitioner_id', user?.id).eq('resource', 'appointments').maybeSingle()
    const cita = ((apptC?.payload as any[]) ?? []).filter(c => c.contactId === p.ghl_contact_id && new Date(c.inicio) >= new Date()).sort((a, b) => +new Date(a.inicio) - +new Date(b.inicio))[0]
    if (cita) ghl.proximaCita = new Date(cita.inicio).toLocaleString('es')
    const { data: contC } = await supabase.from('ghl_cache').select('payload').eq('practitioner_id', user?.id).eq('resource', 'contacts').maybeSingle()
    const cont = ((contC?.payload as any[]) ?? []).find(c => c.id === p.ghl_contact_id)
    if (cont?.origen) ghl.origen = cont.origen
  }

  const portalUrl = `${process.env.NEXT_PUBLIC_APP_URL ?? ''}/portal/${p.access_token}`
  const progress: any[] = (pp?.progress as any[]) ?? []
  const hechos = progress.filter(s => s.done).length

  return (
    <div style={{ maxWidth: 640 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <div style={{ fontSize: 19, fontWeight: 600 }}>{p.full_name}</div>
        <form action={cambiarEstado} style={{ display: 'flex', gap: 8 }}>
          <input type="hidden" name="patient_id" value={p.id} />
          <select name="status" defaultValue={p.status} style={sel}>
            <option value="onboarding">Onboarding</option><option value="activo">Activo</option><option value="pausado">Pausado</option>
          </select>
          <button type="submit" style={btnSm}>Guardar</button>
        </form>
      </div>
      <div style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 18 }}>{p.email || 'Sin email'}{p.phone ? ` · ${p.phone}` : ''}</div>

      {/* Enriquecimiento GHL */}
      {p.ghl_contact_id ? (
        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10, marginBottom: 18 }}>
          <div style={mini}><div style={miniL}>Última conversación</div><div style={miniV}>{ghl.ultimaConv ? (ghl.ultimaConv.length > 40 ? ghl.ultimaConv.slice(0, 40) + '…' : ghl.ultimaConv) : '—'}</div></div>
          <div style={mini}><div style={miniL}>Próxima cita</div><div style={miniV}>{ghl.proximaCita ?? '—'}</div></div>
          <div style={mini}><div style={miniL}>Cómo llegó</div><div style={miniV}>{ghl.origen ?? '—'}</div></div>
        </section>
      ) : (
        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 18 }}>Este paciente aún no está vinculado a tu sistema. Se vincula solo cuando sincronizas (por teléfono o email).</p>
      )}

      {/* Portal */}
      <section style={card}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Su portal privado</div>
        <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12, lineHeight: 1.5 }}>Compártele este link por WhatsApp: ve su protocolo y sus citas, con tu marca.</p>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <CopyButton text={portalUrl} label="Copiar link del portal" />
          <a href={`/portal/${p.access_token}`} target="_blank" style={{ fontSize: 12, color: 'var(--green-l)', textDecoration: 'none' }}>Verlo como él ↗</a>
        </div>
      </section>

      {/* Protocolo */}
      <section style={card}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Su protocolo {pp && <span style={{ color: 'var(--muted)', fontWeight: 400 }}>· {hechos}/{progress.length} pasos</span>}</div>
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
                  <input type="hidden" name="pp_id" value={pp.id} /><input type="hidden" name="idx" value={i} /><input type="hidden" name="patient_id" value={p.id} />
                  <button type="submit" style={{ width: 20, height: 20, borderRadius: '50%', border: '2px solid var(--green)', background: s.done ? 'var(--green)' : 'transparent', color: '#fff', fontSize: 11, cursor: 'pointer', flexShrink: 0 }}>{s.done ? '✓' : ''}</button>
                  <span style={{ fontSize: 13, color: s.done ? 'var(--muted)' : 'var(--ink)', padding: '6px 0' }}>{s.label}</span>
                </form>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Notas de evolución */}
      <section style={card}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 10 }}>Notas de evolución <span style={{ color: 'var(--muted)', fontWeight: 400, fontSize: 11 }}>· privadas, solo tú las ves</span></div>
        <form action={agregarNota} style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
          <input type="hidden" name="patient_id" value={p.id} />
          <input name="body" placeholder="Escribí una nota de seguimiento…" style={{ ...sel, flex: 1 }} />
          <button type="submit" style={btnSm}>Agregar</button>
        </form>
        <div style={{ display: 'grid', gap: 6 }}>
          {(notas ?? []).map(n => (
            <div key={n.id} style={{ fontSize: 13, background: 'var(--bg)', border: '1px solid var(--line)', borderRadius: 8, padding: '9px 11px' }}>
              {n.body}
              <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 3 }}>{new Date(n.created_at).toLocaleString('es')}</div>
            </div>
          ))}
          {(notas?.length ?? 0) === 0 && <p style={{ fontSize: 12, color: 'var(--muted)' }}>Sin notas todavía.</p>}
        </div>
      </section>
    </div>
  )
}

const sel: React.CSSProperties = { background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--ink)', padding: '8px 10px', borderRadius: 8, fontSize: 13, fontFamily: 'inherit' }
const btnSm: React.CSSProperties = { background: 'var(--green)', color: '#fff', border: 'none', padding: '8px 14px', borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: 'pointer' }
const card: React.CSSProperties = { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16, marginBottom: 16 }
const mini: React.CSSProperties = { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 10, padding: '10px 12px' }
const miniL: React.CSSProperties = { fontSize: 11, color: 'var(--muted)', marginBottom: 4 }
const miniV: React.CSSProperties = { fontSize: 12 }
