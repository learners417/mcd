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
  const { data: pract } = await admin.from('practitioners')
    .select('id, full_name').eq('email', email).single()
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
