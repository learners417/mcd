import { createClient } from '@/lib/supabase/server'
import { revalidatePath } from 'next/cache'
import GeneradorIA from './GeneradorIA'

export const dynamic = 'force-dynamic'

async function createProtocol(formData: FormData) {
  'use server'
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  const stepsRaw = String(formData.get('steps') || '')
  const steps = stepsRaw.split('\n').map(s => s.trim()).filter(Boolean)
    .map(label => ({ label, done: false }))
  await supabase.from('protocols').insert({
    practitioner_id: user!.id,
    title: String(formData.get('title')),
    description: String(formData.get('description') || ''),
    steps,
  })
  revalidatePath('/protocolos')
}

/**
 * LA CLÍNICA AMUEBLADA — el método que el sanador construyó en Tu Clínica
 * Digital (tabla compartida `clinica_artefactos`) entra a su clínica con un
 * clic: el protocolo aparece armado, con sus pasos. Idempotente: si ya lo
 * trajo (mismo título), no duplica.
 */
async function importarDeTCD() {
  'use server'
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return
  const { data: art } = await supabase.from('clinica_artefactos')
    .select('metodo_nombre, protocolo')
    .eq('user_id', user.id).maybeSingle()
  if (!art) return
  const title = (art.metodo_nombre || 'Mi método').trim()
  const { data: existente } = await supabase.from('protocols')
    .select('id').eq('practitioner_id', user.id).eq('title', title).maybeSingle()
  if (existente) return
  const steps = String(art.protocolo || '')
    .split('\n').map((s: string) => s.trim()).filter(Boolean)
    .map((label: string) => ({ label, done: false }))
  await supabase.from('protocols').insert({
    practitioner_id: user.id,
    title,
    description: 'Tu método, traído de Tu Clínica Digital.',
    steps: steps.length ? steps : [{ label: 'Revisar y ordenar los pasos de mi método', done: false }],
  })
  revalidatePath('/protocolos')
}

export default async function ProtocolosPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  const { data: protocols } = await supabase.from('protocols')
    .select('id, title, description, steps').order('created_at', { ascending: false })

  // ¿Hay un método esperando en TCD que aún no está acá?
  let artefacto: { metodo_nombre: string | null } | null = null
  try {
    const { data: art } = await supabase.from('clinica_artefactos')
      .select('metodo_nombre, protocolo')
      .eq('user_id', user?.id).maybeSingle()
    if (art && (art.metodo_nombre || art.protocolo)) {
      const titulo = (art.metodo_nombre || 'Mi método').trim()
      const yaEsta = (protocols || []).some((p: any) => p.title === titulo)
      if (!yaEsta) artefacto = { metodo_nombre: art.metodo_nombre }
    }
  } catch { /* sin tabla o sin permiso: la página funciona igual */ }

  return (
    <div>
      <div style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-.02em', marginBottom: 20 }}>Protocolos</div>

      {artefacto && (
        <form action={importarDeTCD}
          style={{ background: 'var(--card)', border: '1px solid var(--green)', borderRadius: 12, padding: 16, marginBottom: 20, display: 'grid', gap: 10, maxWidth: 480 }}>
          <div style={{ fontSize: 15, fontWeight: 600 }}>
            🎁 Tu método te está esperando{artefacto.metodo_nombre ? `: ${artefacto.metodo_nombre}` : ''}
          </div>
          <div style={{ color: 'var(--muted)', fontSize: 13 }}>
            Lo construiste en Tu Clínica Digital. Tráelo con un clic y tu clínica llega amueblada: el protocolo aparece armado, con sus pasos, listo para tus pacientes.
          </div>
          <button type="submit" style={btn}>Traer mi método de TCD</button>
        </form>
      )}

      <GeneradorIA />

      <form action={createProtocol} style={{ display: 'grid', gap: 8, maxWidth: 480, marginBottom: 28 }}>
        <input name="title" required placeholder="Título (ej: Regeneración 12 semanas)" style={inp} />
        <input name="description" placeholder="Descripción corta" style={inp} />
        <textarea name="steps" rows={4} placeholder="Un paso por línea:&#10;Semana 1 — Evaluación&#10;Semana 2 — Ajuste nutricional" style={{ ...inp, resize: 'vertical' }} />
        <button type="submit" style={btn}>Crear protocolo</button>
      </form>

      <div style={{ display: 'grid', gap: 10 }}>
        {(protocols || []).map((p: any) => (
          <div key={p.id} style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16 }}>
            <div style={{ fontSize: 15, fontWeight: 600 }}>{p.title}</div>
            {p.description && <div style={{ color: 'var(--muted)', fontSize: 13, marginTop: 4 }}>{p.description}</div>}
            <div style={{ color: 'var(--muted)', fontSize: 12, marginTop: 8 }}>{(p.steps || []).length} pasos</div>
          </div>
        ))}
        {(protocols?.length ?? 0) === 0 && !artefacto && (
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>Sin protocolos todavía.</p>
        )}
      </div>
    </div>
  )
}

const inp: React.CSSProperties = { background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--ink)', padding: '10px 12px', borderRadius: 9, fontSize: 14, fontFamily: 'inherit' }
const btn: React.CSSProperties = { background: 'var(--green)', color: '#fff', border: 'none', padding: '10px 18px', borderRadius: 9, fontSize: 14, fontWeight: 500, cursor: 'pointer', justifySelf: 'start' }
