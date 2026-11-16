// ============================================================================
//  MCD · Las listas llegan completas — ejecutando la paginación
//
//  POR QUÉ EXISTE. El bloque 6 dice que lo que cuida es que «los contactos se
//  truncan en 100 **en silencio**: faltan personas». Lo medía LEYENDO el
//  cuerpo de la función: que nombrara `startAfterId` y que tuviera techo.
//  Medido el 16 de noviembre: con `page.length < 100` cambiado por
//  `<= 100` —que corta SIEMPRE en la primera página, porque la página nunca
//  trae más de 100— las 74 lentes daban VERDE y un cliente con 300 contactos
//  veía 100. Nadie ejecutaba el lazo.
//
//  Acá se ejecuta contra un GHL de juguete. Corre con:
//  node --experimental-transform-types
// ============================================================================
import { getContacts, getOpportunities, getMessages, getConversations } from '../src/lib/ghl/client.ts'

const AUTH = { token: 'pit-de-juguete', locationId: 'loc-1' }

let fallas = 0
function pide(afirmacion: string, ok: boolean, detalle = '') {
  console.log(`  ${ok ? '✓' : '✗'} ${afirmacion}${ok ? '' : ' — ' + detalle}`)
  if (!ok) fallas++
}

type Llamada = { path: string; params: Record<string, string> }
let llamadas: Llamada[] = []

/** GHL de juguete: `total` contactos, paginando por `startAfterId` como el de verdad. */
function ghlDeJuguete(total: number, extra: (p: Record<string, string>) => any = () => null) {
  llamadas = []
  const contactos = Array.from({ length: total }, (_, i) => ({
    id: `c${i}`, firstName: `Persona${i}`, dateAdded: new Date(2026, 0, 1 + i).toISOString(),
  }))
  globalThis.fetch = (async (url: string) => {
    const u = new URL(String(url))
    const params = Object.fromEntries(u.searchParams.entries())
    llamadas.push({ path: u.pathname, params })
    const propio = extra(params)
    if (propio) return { ok: true, status: 200, json: async () => propio } as any
    if (u.pathname === '/contacts/') {
      const limit = Number(params.limit ?? 100)
      const desde = params.startAfterId
        ? contactos.findIndex(c => c.id === params.startAfterId) + 1
        : 0
      const page = contactos.slice(desde, desde + limit)
      const ultimo = page[page.length - 1]
      return { ok: true, status: 200, json: async () => ({
        contacts: page,
        meta: ultimo ? { startAfterId: ultimo.id, startAfter: Date.parse(ultimo.dateAdded) } : {},
      }) } as any
    }
    if (u.pathname === '/opportunities/search') {
      const limit = Number(params.limit ?? 100), pag = Number(params.page ?? 1)
      const desde = (pag - 1) * limit
      return { ok: true, status: 200, json: async () => ({
        opportunities: Array.from({ length: Math.max(0, Math.min(limit, total - desde)) },
          (_, i) => ({ id: `o${desde + i}` })),
      }) } as any
    }
    return { ok: true, status: 200, json: async () => ({}) } as any
  }) as any
}

console.log('\nLAS LISTAS LLEGAN COMPLETAS\n')

// 1 · las 300 personas de un cliente: las 300, en tres pedidos
ghlDeJuguete(300)
let personas = await getContacts(AUTH)
pide('un cliente con 300 contactos recibe los 300', personas.length === 300,
  `recibió ${personas.length}`)
pide('y sin repetir a nadie', new Set(personas.map((p: any) => p.id)).size === 300,
  `${personas.length - new Set(personas.map((p: any) => p.id)).size} repetidos`)
// 300 son tres páginas llenas y una cuarta vacía: la página llena no dice
// «no hay más», así que hace falta una que vuelva corta. Eso es correcto, y
// queda escrito acá para que nadie lo «arregle» cortando en la primera.
pide('pidiendo página tras página, no una sola vez',
  llamadas.filter(l => l.path === '/contacts/').length === 4,
  `hizo ${llamadas.filter(l => l.path === '/contacts/').length} pedidos`)
pide('y la segunda página pide desde el último de la primera',
  llamadas[1]?.params.startAfterId === 'c99', `pidió desde ${llamadas[1]?.params.startAfterId}`)
pide('el primero y el último de la lista son los de los extremos',
  (personas[0] as any).id === 'c0' && (personas[299] as any).id === 'c299')

// 2 · el caso justo: exactamente 100 no inventa una página vacía de más
ghlDeJuguete(100)
personas = await getContacts(AUTH)
pide('con exactamente 100, llegan 100', personas.length === 100, `llegaron ${personas.length}`)

// 3 · 101: el borde que distingue `<` de `<=`
ghlDeJuguete(101)
personas = await getContacts(AUTH)
pide('con 101, llegan 101 y no 100', personas.length === 101, `llegaron ${personas.length}`)

// 4 · ninguno: no revienta ni cuelga
ghlDeJuguete(0)
personas = await getContacts(AUTH)
pide('un cliente nuevo sin contactos recibe cero, sin error', personas.length === 0)

// 5 · el techo: 1.200 no cuelga la pantalla pidiendo para siempre
ghlDeJuguete(1200)
personas = await getContacts(AUTH)
pide('con 1.200 se detiene en el techo de 1.000', personas.length === 1000,
  `trajo ${personas.length}`)
pide('y no pidió más de once veces', llamadas.length <= 11, `pidió ${llamadas.length} veces`)

// 6 · las ventas, que paginan por número de página
ghlDeJuguete(250)
const ventas = await getOpportunities(AUTH)
pide('250 oportunidades llegan las 250', ventas.length === 250, `llegaron ${ventas.length}`)
pide('y sin repetir', new Set(ventas.map((o: any) => o.id)).size === 250)
pide('la primera página es la 1, no la 0',
  llamadas[0]?.params.page === '1', `pidió la página ${llamadas[0]?.params.page}`)

// 7 · el hilo que GHL devuelve anidado
ghlDeJuguete(0, p => p.limit === '50'
  ? { messages: { messages: [{ id: 'm1', body: 'hola' }, { id: 'm2', body: 'chau' }] } }
  : null)
let hilo = await getMessages(AUTH, 'conv-1')
pide('un hilo anidado en `messages.messages` se desanida',
  Array.isArray(hilo) && hilo.length === 2, `volvió ${JSON.stringify(hilo).slice(0, 60)}`)

// 8 · y el que viene plano, también
ghlDeJuguete(0, p => p.limit === '50' ? { messages: [{ id: 'm1' }] } : null)
hilo = await getMessages(AUTH, 'conv-1')
pide('y uno plano en `messages` llega igual', Array.isArray(hilo) && hilo.length === 1)

// 9 · un hilo vacío es una lista, nunca undefined
ghlDeJuguete(0, p => p.limit === '50' ? {} : null)
hilo = await getMessages(AUTH, 'conv-1')
pide('un hilo sin mensajes es una lista vacía, no `undefined`',
  Array.isArray(hilo) && hilo.length === 0)

// 10 · la bandeja pide el orden que la hace útil
ghlDeJuguete(0, p => p.sortBy ? { conversations: [{ id: 'k1' }] } : null)
await getConversations(AUTH)
const b = llamadas.find(l => l.path === '/conversations/search')
pide('la bandeja pide lo último primero', b?.params.sort === 'desc' &&
  b?.params.sortBy === 'last_message_date', JSON.stringify(b?.params))

console.log(fallas === 0
  ? `\n✓ las listas llegan completas\n`
  : `\n✗ ${fallas} fallas: alguna lista llega cortada\n`)
process.exit(fallas === 0 ? 0 : 1)
