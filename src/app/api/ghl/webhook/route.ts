import crypto from 'crypto'
import { NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/server'
import { syncPractitioner } from '@/lib/ghl/sync'
import { notificar } from '@/lib/notify'

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
  const expected = process.env.GHL_WEBHOOK_SECRET
  if (!secret || !expected || secret.length !== expected.length ||
      !crypto.timingSafeEqual(Buffer.from(secret), Buffer.from(expected))) {
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

  // Notificación según el tipo de evento (la campanita)
  const evento = String(body.type ?? body.eventType ?? '').toLowerCase()
  try {
    if (evento.includes('message') || evento.includes('inbound')) {
      await notificar({ practitionerId: conn.practitioner_id, tipo: 'mensaje',
        titulo: 'Nueva conversación', cuerpo: 'Una persona te escribió por WhatsApp.', link: '/dashboard' })
    } else if (evento.includes('appointment') || evento.includes('booking')) {
      await notificar({ practitionerId: conn.practitioner_id, tipo: 'cita',
        titulo: 'Nueva cita agendada', cuerpo: 'Revisá tu agenda.', link: '/agenda' })
    } else if (evento.includes('opportunity') || evento.includes('stage')) {
      await notificar({ practitionerId: conn.practitioner_id, tipo: 'paciente',
        titulo: 'Movimiento en tu sistema', cuerpo: 'Una persona avanzó en su recorrido.', link: '/personas' })
    }
  } catch { /* recuperable */ }

  // Sync inmediato. AWAIT obligatorio: en Vercel serverless la función se
  // congela al responder — un fire-and-forget jamás terminaría de correr.
  try { await syncPractitioner(conn.practitioner_id, true) } catch { /* recuperable */ }

  return NextResponse.json({ ok: true })
}
