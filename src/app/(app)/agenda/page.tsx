import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export default async function AgendaPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  const { data: me } = await supabase.from('practitioners')
    .select('ghl_calendar_url').eq('id', user?.id).single()

  const url = me?.ghl_calendar_url

  return (
    <div>
      <div style={{ fontSize: 19, fontWeight: 600, marginBottom: 20 }}>Agenda</div>
      {url ? (
        <iframe src={url} style={{ width: '100%', height: '70vh', border: '1px solid var(--line)', borderRadius: 12 }} />
      ) : (
        <div style={{ background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 12, padding: 24, fontSize: 14, color: 'var(--muted)' }}>
          Todavía no conectaste tu calendario. Pegá la URL de tu calendario de GHL
          en <b style={{ color: 'var(--txt)' }}>Mi marca</b> y aparece acá embebido.
          <br /><br />
          <span style={{ fontSize: 12 }}>MVP: el cobro también sale del mismo embed de GHL. Después se reemplaza por integración nativa.</span>
        </div>
      )}
    </div>
  )
}
