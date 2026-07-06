import { NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/server'
import { syncPractitioner } from '@/lib/ghl/sync'

// Receptor de eventos de GHL. Se configura EN EL SNAPSHOT como webhook de
// workflow (mensaje entrante / cita creada / etapa cambiada) apuntando a:
//   https://TU-APP.vercel.app/api/ghl/webhook?secret=GHL_WEBHOOK_SECRET
// Así se configura UNA vez y viaja a cada subcuenta nueva automáticamente.
//
// Estrategia: marcar la cache como vieja + disparar sync. La pantalla "Hoy"
// se refresca sola: un mensaje de WhatsApp nuevo aparece en segundos, no en
// 10 minutos. En WhatsApp, 10 minutos = lead frío.
export async function POST(req: Request) {
  const secret = new URL(req.url).searchParams.get('secret')
  if (!secret || secret !== process.env.GHL_WEBHOOK_SECRET) {
    return NextResponse.json({ error: 'No autorizado' }, { status: 401 })
  }

  const body = await req.json().catch(() => ({}))
  const locationId: string | undefined = body.locationId ?? body.location_id ?? body.location?.id
  if (!locationId) return NextResponse.json({ ok: true, nota: 'Sin locationId, ignorado' })

  const admin = createAdminClient()
  const { data: conn } = await admin.from('ghl_connections')
    .select('practitioner_id').eq('location_id', locationId).single()
  if (!conn) return NextResponse.json({ ok: true, nota: 'Location sin sanador asociado' })

  // Invalidar la cache (fetched_at al pasado) → el próximo load refresca.
  await admin.from('ghl_cache')
    .update({ fetched_at: new Date(0).toISOString() })
    .eq('practitioner_id', conn.practitioner_id)

  // Sync inmediato. AWAIT obligatorio: en Vercel serverless la función se
  // congela al responder — un fire-and-forget jamás terminaría de correr.
  // Si falla no es grave: la cache ya quedó invalidada y el próximo load sincroniza.
  try { await syncPractitioner(conn.practitioner_id, true) } catch { /* recuperable */ }

  return NextResponse.json({ ok: true })
}
