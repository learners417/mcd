import { createClient } from '@/lib/supabase/server'
import CobroForm from './CobroForm'

export const dynamic = 'force-dynamic'

export default async function CobrosPage() {
  const supabase = await createClient()
  const { data: cobros } = await supabase.from('cobros')
    .select('id, amount_usd, concept, paid_at, patients(full_name)')
    .order('paid_at', { ascending: false })
  const { data: patients } = await supabase.from('patients')
    .select('id, full_name').order('full_name')

  const total = (cobros ?? []).reduce((s, c: any) => s + Number(c.amount_usd), 0)

  return (
    <div>
      <div style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-.02em' }}>Cobros</div>
      <div style={{ color: 'var(--muted)', fontSize: 13, marginBottom: 20 }}>
        Cada cobro con su comprobante. {cobros?.length ?? 0} verificados · ${total.toLocaleString('es')} USD en total.
      </div>

      <CobroForm patients={patients ?? []} />

      <div style={{ display: 'grid', gap: 8 }}>
        {(cobros ?? []).map((c: any) => (
          <div key={c.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 10, padding: '12px 14px', fontSize: 13 }}>
            <span>
              <b style={{ color: 'var(--gold)' }}>${Number(c.amount_usd).toLocaleString('es')}</b>
              {c.concept ? ` · ${c.concept}` : ''}
              {c.patients?.full_name ? <span style={{ color: 'var(--muted)' }}> · {c.patients.full_name}</span> : null}
            </span>
            <span style={{ color: 'var(--muted)', display: 'flex', gap: 10, alignItems: 'center' }}>
              <span title="Comprobante adjunto">📎</span>
              {new Date(c.paid_at).toLocaleDateString('es')}
            </span>
          </div>
        ))}
        {(cobros?.length ?? 0) === 0 && (
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>Todavía no registraste cobros. El primero es el que más se festeja.</p>
        )}
      </div>
    </div>
  )
}
