import crypto from 'crypto'
import { NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/server'

// Puente entre las dos apps hermanas. TCD (proyecto Supabase distinto)
// consulta acá los cobros VERIFICADOS de un cliente para:
//   - mover el contador X/10
//   - otorgar el cinturón Rojo (primer pago) sin pedir el comprobante 2 veces
//
// Auth: header  x-integration-key: TCD_INTEGRATION_KEY  (misma clave en ambas apps)
// Uso:  GET /api/integrations/tcd?email=cliente@mail.com
export async function GET(req: Request) {
  // La clave se compara en tiempo constante, igual que el secreto del webhook.
  // Estaba con `!==` pelado: correcto en resultado, pero la comparación corta
  // en el primer carácter distinto, y eso se puede cronometrar desde afuera
  // para adivinar la clave de a un carácter. Son dos puertas al mismo dato —
  // los cobros de un cliente — y no tenían el mismo cerrojo.
  //
  // El largo se compara ANTES porque `timingSafeEqual` tira excepción con
  // buffers de distinto tamaño, y eso sería un 500 en vez de un 401.
  const key = req.headers.get('x-integration-key')
  const expected = process.env.TCD_INTEGRATION_KEY
  if (!key || !expected || key.length !== expected.length ||
      !crypto.timingSafeEqual(Buffer.from(key), Buffer.from(expected))) {
    return NextResponse.json({ error: 'No autorizado' }, { status: 401 })
  }

  const email = new URL(req.url).searchParams.get('email')?.toLowerCase()
  if (!email) return NextResponse.json({ error: 'Falta ?email=' }, { status: 400 })

  const admin = createAdminClient()

  // La búsqueda es por email y NO distingue mayúsculas, por dos razones.
  //
  // La primera: el índice que existe para esto es `on practitioners(lower(email))`
  // —se creó el 8 de julio junto con la columna— y un `.eq('email', …)` pelado
  // no lo usa ni respeta su intención. El email entra en minúsculas desde el
  // puente de TCD, pero la columna guarda lo que escribió el trigger o lo que
  // cargó una mano: una sola mayúscula guardada y este endpoint contesta 404.
  //
  // La segunda: ese 404 no se lee como «no lo encuentro». Del otro lado del
  // puente se traduce a «todavía no cobró», y entonces el cliente que vendió
  // se queda sin su Cinturón Rojo y con el día 31 trabado, en silencio.
  //
  // El camino normal sigue siendo el exacto. La barrida sin mayúsculas sólo
  // corre cuando el exacto no encontró nada, y su resultado se vuelve a
  // verificar en JS: `ilike` trata `_` y `%` como comodines —y el `_` es
  // legal y común en un email—, así que lo que vuelve se compara entero.
  let { data: pract } = await admin.from('practitioners')
    .select('id, full_name, email').eq('email', email).maybeSingle()

  if (!pract) {
    const { data: parecidos } = await admin.from('practitioners')
      .select('id, full_name, email').ilike('email', email)
    pract = (parecidos ?? []).find(p => p.email?.toLowerCase() === email) ?? null
  }

  if (!pract) return NextResponse.json({ error: 'Cliente no encontrado en MCD' }, { status: 404 })

  const { data: cobros } = await admin.from('cobros')
    .select('id, amount_usd, concept, paid_at')
    .eq('practitioner_id', pract.id)
    .order('paid_at', { ascending: true })

  const lista = cobros ?? []
  return NextResponse.json({
    email,
    nombre: pract.full_name,
    cobros_verificados: lista.length,          // ← el X del X/10
    total_usd: lista.reduce((s, c) => s + Number(c.amount_usd), 0),
    primer_cobro: lista[0]?.paid_at ?? null,    // ← dispara el cinturón Rojo
    cobros: lista,
  })
}
