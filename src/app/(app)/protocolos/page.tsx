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

export default async function ProtocolosPage() {
  const supabase = await createClient()
  const { data: protocols } = await supabase.from('protocols')
    .select('id, title, description, steps').order('created_at', { ascending: false })

  return (
    <div>
      <div style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-.02em', marginBottom: 20 }}>Protocolos</div>

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
        {(protocols?.length ?? 0) === 0 && (
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>Sin protocolos todavía.</p>
        )}
      </div>
    </div>
  )
}

const inp: React.CSSProperties = { background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--ink)', padding: '10px 12px', borderRadius: 9, fontSize: 14, fontFamily: 'inherit' }
const btn: React.CSSProperties = { background: 'var(--green)', color: '#fff', border: 'none', padding: '10px 18px', borderRadius: 9, fontSize: 14, fontWeight: 500, cursor: 'pointer', justifySelf: 'start' }
