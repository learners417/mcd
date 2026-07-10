// MCD · Crear notificaciones (server-only, admin client)
// Con dedup: no repite la misma notificación (mismo tipo+link) si ya hay una
// sin leer en los últimos 10 min. Evita que 5 mensajes = 5 campanitas iguales.
import { createAdminClient } from '@/lib/supabase/server'

export async function notificar(params: {
  practitionerId: string; tipo: string; titulo: string; cuerpo?: string; link?: string
}) {
  const admin = createAdminClient()

  const desde = new Date(Date.now() - 10 * 60 * 1000).toISOString()
  const { data: reciente } = await admin.from('notifications')
    .select('id')
    .eq('practitioner_id', params.practitionerId)
    .eq('tipo', params.tipo)
    .eq('leida', false)
    .gte('created_at', desde)
    .limit(1)

  // Ya hay una sin leer del mismo tipo hace poco → no duplicar
  if (reciente && reciente.length > 0) return

  await admin.from('notifications').insert({
    practitioner_id: params.practitionerId,
    tipo: params.tipo,
    titulo: params.titulo,
    cuerpo: params.cuerpo ?? null,
    link: params.link ?? null,
  })
}
