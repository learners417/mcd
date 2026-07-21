import { createClient } from '@/lib/supabase/server'
import { revalidatePath } from 'next/cache'

export const dynamic = 'force-dynamic'

async function guardar(formData: FormData) {
  'use server'
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  await supabase.from('practitioners').update({
    brand_name: String(formData.get('brand_name') || ''),
    specialty: String(formData.get('specialty') || ''),
    brand_color: String(formData.get('brand_color') || '#3D6B4F'),
    ghl_calendar_url: String(formData.get('ghl_calendar_url') || '') || null,
    inversion_mensual: Number(formData.get('inversion_mensual') || 0),
  }).eq('id', user!.id)
  revalidatePath('/marca'); revalidatePath('/dashboard'); revalidatePath('/agenda')
}

export default async function MarcaPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  const { data: me } = await supabase.from('practitioners').select('*').eq('id', user?.id).single()

  // LA CLÍNICA AMUEBLADA — si la marca está vacía, precargamos su identidad
  // desde Tu Clínica Digital (tabla compartida `profiles`). Guarda y queda.
  let tcdNombre = ''
  let tcdEspecialidad = ''
  if (!me?.brand_name || !me?.specialty) {
    try {
      const { data: perfilTCD } = await supabase.from('profiles')
        .select('nombre, especialidad').eq('id', user?.id).maybeSingle()
      tcdNombre = String(perfilTCD?.nombre ?? '')
      tcdEspecialidad = String(perfilTCD?.especialidad ?? '')
    } catch { /* sin tabla o sin permiso: la página funciona igual */ }
  }
  const precargado = (!me?.brand_name && tcdNombre) || (!me?.specialty && tcdEspecialidad)

  return (
    <div style={{ maxWidth: 520 }}>
      <div style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-.02em', marginBottom: 4 }}>Mi marca</div>
      <div style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 22 }}>
        Así te ven tus pacientes en su portal. Tu marca, no la nuestra.
      </div>
      {precargado && (
        <div style={{ background: 'var(--card)', border: '1px solid var(--green)', borderRadius: 10, padding: '10px 14px', fontSize: 13, color: 'var(--muted)', marginBottom: 16 }}>
          🎁 Precargamos tu nombre y especialidad desde Tu Clínica Digital — revisa y guarda para confirmar.
        </div>
      )}

      <form action={guardar} style={{ display: 'grid', gap: 12 }}>
        <label style={lbl}>Nombre profesional (como te presentas)
          <input name="brand_name" defaultValue={me?.brand_name || tcdNombre || ''} placeholder="Dra. Evelyn Bernal" style={inp} />
        </label>
        <label style={lbl}>Especialidad
          <input name="specialty" defaultValue={me?.specialty || tcdEspecialidad || ''} placeholder="Medicina Regenerativa" style={inp} />
        </label>
        <label style={lbl}>Color de tu marca (el portal del paciente lo usa)
          <input name="brand_color" type="color" defaultValue={me?.brand_color ?? '#3D6B4F'}
            style={{ ...inp, padding: 4, height: 44, width: 90, cursor: 'pointer' }} />
        </label>
        <label style={lbl}>Tu inversión mensual en anuncios (USD) — el panel te muestra el retorno
          <input name="inversion_mensual" type="number" min="0" step="1" defaultValue={me?.inversion_mensual ?? ''} placeholder="ej: 450" style={inp} />
        </label>
        <label style={lbl}>Link de tu calendario (te lo entrega el equipo — pégalo aquí y aparece en Agenda)
          <input name="ghl_calendar_url" defaultValue={me?.ghl_calendar_url ?? ''} placeholder="https://..." style={inp} />
        </label>
        <button type="submit" style={btn}>Guardar</button>
      </form>
    </div>
  )
}

const lbl: React.CSSProperties = { fontSize: 12, color: 'var(--muted)', display: 'grid', gap: 6 }
const inp: React.CSSProperties = { background: 'var(--card)', border: '1px solid var(--line)', color: 'var(--ink)', padding: '11px 12px', borderRadius: 9, fontSize: 14, fontFamily: 'inherit' }
const btn: React.CSSProperties = { background: 'var(--green)', color: '#fff', border: 'none', padding: '11px 20px', borderRadius: 9, fontSize: 14, fontWeight: 500, cursor: 'pointer', justifySelf: 'start', marginTop: 6 }
