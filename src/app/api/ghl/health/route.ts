import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { getConnection } from '@/lib/ghl/sync'
import { getCalendars } from '@/lib/ghl/client'
import { decryptToken } from '@/lib/crypto'

// Chequeo en vivo: ¿el token de la subcuenta responde?
// Uso: logueate y abrí /api/ghl/health en el navegador.
export async function GET() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'No autenticado' }, { status: 401 })

  const conn = await getConnection(user.id)
  if (!conn) return NextResponse.json({ ok: false, detalle: 'Sin conexión GHL cargada para este usuario' })
  if (!conn.private_token) return NextResponse.json({ ok: false, detalle: 'Conexión sin token: falta cargar el PIT' })

  try {
    const calendars = await getCalendars({ token: decryptToken(conn.private_token), locationId: conn.location_id })
    return NextResponse.json({
      ok: true,
      locationId: conn.location_id,
      calendarios: calendars.map((c: any) => c.name),
      ultimoSync: conn.last_sync_at,
    })
  } catch (e: any) {
    return NextResponse.json({ ok: false, detalle: e.message }, { status: 502 })
  }
}
