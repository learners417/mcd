import { createClient } from '@/lib/supabase/server'
import { revalidatePath } from 'next/cache'

export const dynamic = 'force-dynamic'

async function guardar(formData: FormData) {
  'use server'
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  await supabase.from('agent_config').upsert({
    practitioner_id: user!.id,
    tono: String(formData.get('tono') || ''),
    reglas: String(formData.get('reglas') || ''),
    firma: String(formData.get('firma') || ''),
    updated_at: new Date().toISOString(),
  })
  revalidatePath('/asistente')
}

export default async function AsistentePage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  const { data: cfg } = await supabase.from('agent_config').select('*').eq('practitioner_id', user?.id).maybeSingle()

  return (
    <div style={{ maxWidth: 560 }}>
      <div style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-.02em', marginBottom: 4 }}>Tu Asistente ✨</div>
      <div style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 22, lineHeight: 1.6 }}>
        Configura cómo te ayuda la IA a responder mensajes. Cuando redacta o sugiere en tus
        conversaciones, usa este tono y estas reglas — para que suene a ti, no a un robot.
      </div>
      <form action={guardar} style={{ display: 'grid', gap: 12 }}>
        <label style={lbl}>Tono de tus mensajes
          <input name="tono" defaultValue={cfg?.tono ?? 'cálido y profesional'} placeholder="cálido y profesional" style={inp} />
        </label>
        <label style={lbl}>Reglas (qué decir y qué evitar)
          <textarea name="reglas" defaultValue={cfg?.reglas ?? ''} rows={4} placeholder="Ej: nunca doy precios por mensaje, siempre invito a una llamada. Trato de tú." style={{ ...inp, resize: 'vertical' }} />
        </label>
        <label style={lbl}>Firma (cómo cerrás tus mensajes)
          <input name="firma" defaultValue={cfg?.firma ?? ''} placeholder="Un abrazo, Dra. Evelyn" style={inp} />
        </label>
        <button type="submit" style={btn}>Guardar</button>
      </form>
    </div>
  )
}
const lbl: React.CSSProperties = { fontSize: 12, color: 'var(--muted)', display: 'grid', gap: 6 }
const inp: React.CSSProperties = { background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--ink)', padding: '11px 12px', borderRadius: 9, fontSize: 14, fontFamily: 'inherit' }
const btn: React.CSSProperties = { background: 'var(--green)', color: '#fff', border: 'none', padding: '11px 20px', borderRadius: 9, fontSize: 14, fontWeight: 500, cursor: 'pointer', justifySelf: 'start' }
