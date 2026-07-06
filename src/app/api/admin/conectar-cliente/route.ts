import { NextResponse } from 'next/server'
import { createClient, createAdminClient } from '@/lib/supabase/server'
import { createSubaccount } from '@/lib/ghl/client'
import { encryptToken } from '@/lib/crypto'

// SOLO admin (Javo). Onboarding de un cliente nuevo en 2 modos:
//
// MODO A — subcuenta YA existe (creada a mano en GHL):
//   { practitioner_id, location_id, private_token }
//   → solo guarda la conexión.
//
// MODO B — crear subcuenta + Snapshot por API (Agency Pro):
//   { practitioner_id, create: { name, email?, phone?, country? }, private_token? }
//   → crea la location con GHL_SNAPSHOT_ID, guarda location_id.
//   El PIT de la subcuenta nueva se genera en el dashboard de GHL y se
//   agrega después con MODO A (GHL no emite PITs por API).
//
// Requiere en .env: ADMIN_EMAIL, GHL_AGENCY_TOKEN, GHL_COMPANY_ID, GHL_SNAPSHOT_ID
export async function POST(req: Request) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user || user.email !== process.env.ADMIN_EMAIL) {
    return NextResponse.json({ error: 'Solo admin' }, { status: 403 })
  }

  const body = await req.json()
  if (!body.practitioner_id || typeof body.practitioner_id !== 'string') {
    return NextResponse.json({ error: 'Falta practitioner_id' }, { status: 400 })
  }
  const admin = createAdminClient()
  let locationId: string = body.location_id

  // MODO B: crear la subcuenta con el Snapshot
  if (!locationId && body.create) {
    const agencyToken = process.env.GHL_AGENCY_TOKEN
    const companyId = process.env.GHL_COMPANY_ID
    if (!agencyToken || !companyId) {
      return NextResponse.json({ error: 'Faltan GHL_AGENCY_TOKEN / GHL_COMPANY_ID en env' }, { status: 500 })
    }
    const loc = await createSubaccount(agencyToken, {
      name: body.create.name,
      companyId,
      snapshotId: process.env.GHL_SNAPSHOT_ID,
      email: body.create.email,
      phone: body.create.phone,
      country: body.create.country,
    })
    locationId = loc.id ?? loc.location?.id
  }

  if (!locationId) return NextResponse.json({ error: 'Falta location_id o create{}' }, { status: 400 })

  const { error } = await admin.from('ghl_connections').upsert({
    practitioner_id: body.practitioner_id,
    location_id: locationId,
    // El token se guarda CIFRADO (AES-256-GCM). null = pendiente de PIT.
    private_token: body.private_token ? encryptToken(String(body.private_token)) : null,
    company_id: process.env.GHL_COMPANY_ID ?? null,
  })
  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  return NextResponse.json({
    ok: true,
    location_id: locationId,
    nota: body.private_token ? 'Conexión completa' : 'Subcuenta creada. Generá el PIT en GHL y repetí la llamada con private_token.',
  })
}
