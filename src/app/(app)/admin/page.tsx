import { createClient, createAdminClient } from '@/lib/supabase/server'
import { encryptToken } from '@/lib/crypto'
import { redirect } from 'next/navigation'
import { revalidatePath } from 'next/cache'

export const dynamic = 'force-dynamic'

// SOLO Javo (ADMIN_EMAIL). El onboarding de un cliente en una pantalla:
// elegir sanador → pegar Location ID + PIT → conectado.
async function setInversion(formData: FormData) {
  'use server'
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user || user.email !== process.env.ADMIN_EMAIL) return
  const admin = createAdminClient()
  await admin.from('practitioners').update({
    inversion_mensual: Number(formData.get('inversion_mensual') || 0),
  }).eq('id', String(formData.get('practitioner_id')))
  revalidatePath('/admin')
}

async function conectar(formData: FormData) {
  'use server'
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user || user.email !== process.env.ADMIN_EMAIL) return

  const admin = createAdminClient()
  await admin.from('ghl_connections').upsert({
    practitioner_id: String(formData.get('practitioner_id')),
    location_id: String(formData.get('location_id')).trim(),
    private_token: formData.get('private_token')
      ? encryptToken(String(formData.get('private_token')).trim())
      : null,
    company_id: process.env.GHL_COMPANY_ID ?? null,
  })
  revalidatePath('/admin')
}

export default async function AdminPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user || user.email !== process.env.ADMIN_EMAIL) redirect('/dashboard')

  const admin = createAdminClient()
  const { data: pracs } = await admin.from('practitioners')
    .select('id, full_name, email, created_at, inversion_mensual').order('created_at', { ascending: false })
  const { data: conns } = await admin.from('ghl_connections')
    .select('practitioner_id, location_id, private_token, last_sync_at')
  const connMap = new Map((conns ?? []).map(c => [c.practitioner_id, c]))

  return (
    <div style={{ maxWidth: 760 }}>
      <div style={{ fontSize: 19, fontWeight: 600, marginBottom: 4 }}>Admin · Conexiones GHL</div>
      <div style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 22 }}>
        El alta de un cliente: crear su subcuenta en GHL con el Snapshot → generar su
        Private Integration Token → conectarlo acá. El token se guarda cifrado.
      </div>

      <form action={conectar} style={{ display: 'grid', gap: 8, gridTemplateColumns: '1fr 1fr', background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 16, marginBottom: 24 }}>
        <select name="practitioner_id" required defaultValue="" style={{ ...inp, gridColumn: '1 / -1' }}>
          <option value="" disabled>Elegí el sanador…</option>
          {(pracs ?? []).map(p => (
            <option key={p.id} value={p.id}>{p.full_name} — {p.email ?? 'sin email'}</option>
          ))}
        </select>
        <input name="location_id" required placeholder="Location ID de la subcuenta" style={inp} />
        <input name="private_token" placeholder="Private Integration Token (o vacío si aún no)" style={inp} />
        <button type="submit" style={{ ...btn, gridColumn: '1 / -1' }}>Conectar / actualizar</button>
      </form>

      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>Clientes ({pracs?.length ?? 0})</div>
      <div style={{ display: 'grid', gap: 8 }}>
        {(pracs ?? []).map(p => {
          const c = connMap.get(p.id)
          const estado = !c ? '○ sin conexión' : !c.private_token ? '◐ falta el token' : '● conectado'
          const color = !c ? 'var(--muted)' : !c.private_token ? 'var(--gold)' : 'var(--green-l)'
          return (
            <div key={p.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 10, padding: '12px 14px', fontSize: 13 }}>
              <span><b>{p.full_name}</b> <span style={{ color: 'var(--muted)' }}>· {p.email ?? '—'}</span></span>
              <span style={{ display: 'flex', gap: 14, alignItems: 'center', fontSize: 12 }}>
                <form action={setInversion} style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                  <input type="hidden" name="practitioner_id" value={p.id} />
                  <span style={{ color: 'var(--muted)' }}>$/mes</span>
                  <input name="inversion_mensual" type="number" defaultValue={p.inversion_mensual ?? 0}
                    style={{ width: 60, background: 'var(--bg)', border: '1px solid var(--line)', color: 'var(--ink)', padding: '4px 6px', borderRadius: 6, fontSize: 12, fontFamily: 'inherit' }} />
                  <button type="submit" style={{ background: 'transparent', border: '1px solid var(--line)', color: 'var(--muted)', padding: '4px 8px', borderRadius: 6, fontSize: 11, cursor: 'pointer' }}>✓</button>
                </form>
                {c?.last_sync_at && <span style={{ color: 'var(--muted)' }}>sync {new Date(c.last_sync_at).toLocaleString('es', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>}
                <span style={{ color }}>{estado}</span>
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

const inp: React.CSSProperties = { background: 'var(--bg)', border: '1px solid var(--line)', color: 'var(--ink)', padding: '10px 12px', borderRadius: 9, fontSize: 13, fontFamily: 'inherit' }
const btn: React.CSSProperties = { background: 'var(--green)', color: '#fff', border: 'none', padding: '10px 18px', borderRadius: 9, fontSize: 13, fontWeight: 500, cursor: 'pointer' }
