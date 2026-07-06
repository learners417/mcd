import { createClient } from '@/lib/supabase/server'
import { revalidatePath } from 'next/cache'
import Link from 'next/link'

export const dynamic = 'force-dynamic'

async function addPatient(formData: FormData) {
  'use server'
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  await supabase.from('patients').insert({
    practitioner_id: user!.id,
    full_name: String(formData.get('full_name')),
    email: String(formData.get('email') || ''),
    status: 'onboarding',
  })
  revalidatePath('/pacientes')
}

export default async function PacientesPage() {
  const supabase = await createClient()
  const { data: patients } = await supabase.from('patients')
    .select('id, full_name, status, access_token').order('created_at', { ascending: false })

  return (
    <div>
      <div style={{ fontSize: 19, fontWeight: 600, marginBottom: 20 }}>Pacientes</div>

      {/* alta rápida — Server Action */}
      <form action={addPatient} style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
        <input name="full_name" required placeholder="Nombre del paciente"
          style={inp} />
        <input name="email" type="email" placeholder="Email (opcional)" style={inp} />
        <button type="submit" style={btn}>Agregar</button>
      </form>

      <div style={{ display: 'grid', gap: 8 }}>
        {(patients || []).map(p => (
          <Link key={p.id} href={`/pacientes/${p.id}`}
            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 10, padding: '12px 14px', fontSize: 14, textDecoration: 'none', color: 'var(--txt)' }}>
            <span>{p.full_name}</span>
            <span style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: p.status === 'activo' ? 'var(--green-l)' : 'var(--muted)' }}>{p.status}</span>
              <span style={{ fontSize: 12, color: 'var(--muted)' }}>abrir ficha →</span>
            </span>
          </Link>
        ))}
        {(patients?.length ?? 0) === 0 && (
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>Todavía no cargaste pacientes.</p>
        )}
      </div>
    </div>
  )
}

const inp: React.CSSProperties = { background: 'var(--panel)', border: '1px solid var(--line)', color: 'var(--txt)', padding: '10px 12px', borderRadius: 9, fontSize: 14, fontFamily: 'inherit' }
const btn: React.CSSProperties = { background: 'var(--green)', color: '#fff', border: 'none', padding: '10px 18px', borderRadius: 9, fontSize: 14, fontWeight: 500, cursor: 'pointer' }
