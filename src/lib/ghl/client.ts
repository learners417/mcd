// ============================================================================
//  MCD · Capa GHL · Cliente de API v2 (server-only)
//  Base: https://services.leadconnectorhq.com · Header Version: 2021-07-28
//
//  REGLAS:
//  - Solo se importa desde código server-side. El token JAMÁS toca el browser.
//  - Timeout 15s + 2 reintentos con backoff en 429/5xx.
//  - Paginación hasta MAX_ITEMS para no truncar silenciosamente.
//  - Normalización para la UI vive en normalize.ts, no acá.
// ============================================================================

const GHL_BASE = 'https://services.leadconnectorhq.com'
const GHL_VERSION = '2021-07-28'
const TIMEOUT_MS = 15_000
const MAX_ITEMS = 1_000

type GhlAuth = { token: string; locationId: string }

export class GhlError extends Error {
  constructor(public status: number, public path: string, public body: string) {
    super(`GHL ${status} en ${path}: ${body.slice(0, 300)}`)
  }
}

async function ghlFetch(
  auth: GhlAuth,
  path: string,
  params: Record<string, string | number | undefined> = {},
  attempt = 0
): Promise<any> {
  const url = new URL(GHL_BASE + path)
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined) url.searchParams.set(k, String(v))
  }
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS)
  try {
    const res = await fetch(url.toString(), {
      headers: {
        Authorization: `Bearer ${auth.token}`,
        Version: GHL_VERSION,
        Accept: 'application/json',
      },
      cache: 'no-store',
      signal: ctrl.signal,
    })
    // Retry en rate-limit o error de servidor
    if ((res.status === 429 || res.status >= 500) && attempt < 2) {
      await new Promise(r => setTimeout(r, 600 * (attempt + 1)))
      return ghlFetch(auth, path, params, attempt + 1)
    }
    if (!res.ok) throw new GhlError(res.status, path, await res.text().catch(() => ''))
    return res.json()
  } catch (e: any) {
    if (e.name === 'AbortError' && attempt < 2) {
      return ghlFetch(auth, path, params, attempt + 1)
    }
    throw e
  } finally {
    clearTimeout(timer)
  }
}

// ---------------------------------------------------------------------------
// CONTACTS — las "Personas". Paginado (un cliente con 300 contactos debe
// verlos TODOS, no los primeros 100).
// ---------------------------------------------------------------------------
export async function getContacts(auth: GhlAuth) {
  const all: any[] = []
  let startAfterId: string | undefined
  let startAfter: number | undefined
  while (all.length < MAX_ITEMS) {
    const data = await ghlFetch(auth, '/contacts/', {
      locationId: auth.locationId,
      limit: 100,
      startAfterId,
      startAfter,
    })
    const page = data.contacts ?? []
    all.push(...page)
    if (page.length < 100) break
    const last = page[page.length - 1]
    startAfterId = data.meta?.startAfterId ?? last.id
    startAfter = data.meta?.startAfter ?? (last.dateAdded ? new Date(last.dateAdded).getTime() : undefined)
    if (!startAfterId) break
  }
  return all
}

// ---------------------------------------------------------------------------
// CONVERSATIONS — WhatsApp/KAI. La bandeja: lo más valioso de la máscara.
// ---------------------------------------------------------------------------
export async function getConversations(auth: GhlAuth, limit = 100) {
  const data = await ghlFetch(auth, '/conversations/search', {
    locationId: auth.locationId,
    limit,
    sort: 'desc',
    sortBy: 'last_message_date',
  })
  return data.conversations ?? []
}

// ---------------------------------------------------------------------------
// CALENDARS + EVENTS — la Agenda
// ---------------------------------------------------------------------------
export async function getCalendars(auth: GhlAuth) {
  const data = await ghlFetch(auth, '/calendars/', { locationId: auth.locationId })
  return data.calendars ?? []
}

export async function getCalendarEvents(
  auth: GhlAuth, calendarId: string, fromMs: number, toMs: number
) {
  const data = await ghlFetch(auth, '/calendars/events', {
    locationId: auth.locationId,
    calendarId,
    startTime: fromMs,
    endTime: toMs,
  })
  return data.events ?? []
}

export async function getAllEvents(auth: GhlAuth, fromMs: number, toMs: number) {
  const calendars = await getCalendars(auth)
  const batches = await Promise.all(
    calendars.map((c: any) => getCalendarEvents(auth, c.id, fromMs, toMs).catch(() => []))
  )
  return { calendars, events: batches.flat() }
}

// ---------------------------------------------------------------------------
// PIPELINES + OPPORTUNITIES — el "Sistema de Ventas"
// OJO: /opportunities/search usa location_id (snake_case). Rareza de GHL.
// ---------------------------------------------------------------------------
export async function getPipelines(auth: GhlAuth) {
  const data = await ghlFetch(auth, '/opportunities/pipelines', { locationId: auth.locationId })
  return data.pipelines ?? []
}

export async function getOpportunities(auth: GhlAuth) {
  const all: any[] = []
  let page = 1
  while (all.length < MAX_ITEMS) {
    const data = await ghlFetch(auth, '/opportunities/search', {
      location_id: auth.locationId,
      limit: 100,
      page,
    })
    const batch = data.opportunities ?? []
    all.push(...batch)
    if (batch.length < 100) break
    page += 1
  }
  return all
}

// ---------------------------------------------------------------------------
// AGENCY (plan Agency Pro) — crear subcuenta + cargar Snapshot.
// Panel admin de Javo. Requiere token de AGENCIA (no el PIT de subcuenta).
// ---------------------------------------------------------------------------
export async function createSubaccount(agencyToken: string, params: {
  name: string; companyId: string; snapshotId?: string
  email?: string; phone?: string; country?: string; timezone?: string
}) {
  const res = await fetch(`${GHL_BASE}/locations/`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${agencyToken}`,
      Version: GHL_VERSION,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      name: params.name,
      companyId: params.companyId,
      ...(params.snapshotId ? { snapshotId: params.snapshotId } : {}),
      ...(params.email ? { email: params.email } : {}),
      ...(params.phone ? { phone: params.phone } : {}),
      country: params.country ?? 'EC',
      timezone: params.timezone ?? 'America/Guayaquil',
    }),
    cache: 'no-store',
  })
  if (!res.ok) throw new GhlError(res.status, '/locations/', await res.text())
  return res.json()
}
