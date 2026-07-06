// ============================================================================
//  MCD · Capa GHL · Motor de sync
//  Pull de GHL → normalizar → cache en Supabase (ghl_cache).
//  La UI SIEMPRE lee de ghl_cache (RLS: cada sanador lee lo suyo).
//  Este módulo corre SOLO server-side con el admin client (service role).
// ============================================================================

import { createAdminClient } from '@/lib/supabase/server'
import { decryptToken } from '@/lib/crypto'
import * as ghl from './client'
import {
  toPersona, toConversacion, toCita, toVenta, stageNameIndex,
} from './normalize'

const STALE_MINUTES = 10

export type SyncResult = {
  ok: boolean
  refreshed: string[]          // recursos actualizados
  skipped: string[]            // recursos aún frescos
  errors: Record<string, string>
}

/** Trae la conexión GHL del sanador (server-only). null = no conectado aún. */
export async function getConnection(practitionerId: string) {
  const admin = createAdminClient()
  const { data } = await admin.from('ghl_connections')
    .select('location_id, private_token, last_sync_at')
    .eq('practitioner_id', practitionerId).single()
  return data ?? null
}

/**
 * Sincroniza todos los recursos de la máscara para un sanador.
 * force=true ignora la ventana de frescura (botón "Actualizar" en la UI).
 */
export async function syncPractitioner(
  practitionerId: string,
  force = false
): Promise<SyncResult> {
  const admin = createAdminClient()
  const result: SyncResult = { ok: true, refreshed: [], skipped: [], errors: {} }

  const conn = await getConnection(practitionerId)
  if (!conn) {
    return { ok: false, refreshed: [], skipped: [], errors: { connection: 'Sin conexión GHL para este sanador' } }
  }
  if (!conn.private_token) {
    // Subcuenta creada pero PIT aún no cargado: salir limpio, sin 401 en cadena.
    return { ok: false, refreshed: [], skipped: [], errors: { connection: 'Conexión sin token: generá el PIT en GHL y cargalo' } }
  }
  const auth = { token: decryptToken(conn.private_token), locationId: conn.location_id }

  // ¿Qué está viejo?
  const { data: cacheRows } = await admin.from('ghl_cache')
    .select('resource, fetched_at').eq('practitioner_id', practitionerId)
  const freshUntil = new Map(
    (cacheRows ?? []).map(r => [r.resource, new Date(r.fetched_at).getTime() + STALE_MINUTES * 60_000])
  )
  const isFresh = (res: string) => !force && (freshUntil.get(res) ?? 0) > Date.now()

  async function save(resource: string, payload: unknown) {
    await admin.from('ghl_cache').upsert({
      practitioner_id: practitionerId,
      resource,
      payload,
      fetched_at: new Date().toISOString(),
    }, { onConflict: 'practitioner_id,resource' })
    result.refreshed.push(resource)
  }

  // --- personas (contacts) ---
  if (isFresh('contacts')) result.skipped.push('contacts')
  else try {
    const raw = await ghl.getContacts(auth)
    await save('contacts', raw.map(toPersona))
  } catch (e: any) { result.errors.contacts = e.message; result.ok = false }

  // --- conversaciones ---
  if (isFresh('conversations')) result.skipped.push('conversations')
  else try {
    const raw = await ghl.getConversations(auth)
    await save('conversations', raw.map(toConversacion))
  } catch (e: any) { result.errors.conversations = e.message; result.ok = false }

  // --- agenda: hoy-7d → hoy+30d ---
  if (isFresh('appointments')) result.skipped.push('appointments')
  else try {
    const from = Date.now() - 7 * 86_400_000
    const to = Date.now() + 30 * 86_400_000
    const { calendars, events } = await ghl.getAllEvents(auth, from, to)
    await save('appointments', events.map(toCita))
    await save('calendars', calendars.map((c: any) => ({ id: c.id, nombre: c.name })))
  } catch (e: any) { result.errors.appointments = e.message; result.ok = false }

  // --- sistema de ventas (pipeline) ---
  if (isFresh('opportunities')) result.skipped.push('opportunities')
  else try {
    const pipelines = await ghl.getPipelines(auth)
    const idx = stageNameIndex(pipelines)
    const raw = await ghl.getOpportunities(auth)
    await save('opportunities', raw.map((o: any) => toVenta(o, idx)))
  } catch (e: any) { result.errors.opportunities = e.message; result.ok = false }

  await admin.from('ghl_connections')
    .update({ last_sync_at: new Date().toISOString() })
    .eq('practitioner_id', practitionerId)

  return result
}

/** Lectura tipada de la cache (para Server Components de la UI). */
export async function readCache<T = any>(
  practitionerId: string,
  resource: string
): Promise<{ items: T[]; fetchedAt: string | null }> {
  const admin = createAdminClient()
  const { data } = await admin.from('ghl_cache')
    .select('payload, fetched_at')
    .eq('practitioner_id', practitionerId).eq('resource', resource).single()
  return {
    items: (data?.payload as T[]) ?? [],
    fetchedAt: data?.fetched_at ?? null,
  }
}

/**
 * Sync suave para las pantallas: si hay conexión y la cache está vieja,
 * refresca; si falla, silencio — la UI muestra la cache que haya.
 */
export async function ensureFresh(practitionerId: string) {
  try {
    const conn = await getConnection(practitionerId)
    if (!conn?.private_token) return
    await syncPractitioner(practitionerId, false)
  } catch { /* recuperable: se muestra la cache existente */ }
}
