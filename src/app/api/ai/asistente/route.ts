import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { redactarRespuesta, resumirConversacion, sugerirProximoPaso, generarProtocolo } from '@/lib/ai/asistente'
import { getConnection } from '@/lib/ghl/sync'
import { decryptToken } from '@/lib/crypto'
import { getMessages } from '@/lib/ghl/client'
import { toMensaje } from '@/lib/ghl/normalize'

// POST /api/ai/asistente
// { tarea: 'redactar'|'resumir'|'sugerir'|'protocolo', ...datos }
// Rate-limit simple en memoria: máx 1 llamada cada 2s por usuario.
// Evita que un doble-click dispare llamadas duplicadas al proxy.
const ultimaLlamada = new Map<string, number>()

export async function POST(req: Request) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'No autenticado' }, { status: 401 })

  const ahora = Date.now()
  const prev = ultimaLlamada.get(user.id) ?? 0
  if (ahora - prev < 2000) return NextResponse.json({ error: 'Esperá un momento…' }, { status: 429 })
  ultimaLlamada.set(user.id, ahora)

  const body = await req.json()
  const { data: me } = await supabase.from('practitioners')
    .select('brand_name, specialty').eq('id', user.id).single()
  const { data: cfg } = await supabase.from('agent_config')
    .select('*').eq('practitioner_id', user.id).maybeSingle()

  const config = {
    tono: cfg?.tono, reglas: cfg?.reglas, firma: cfg?.firma,
    marca: me?.brand_name, especialidad: me?.specialty,
  }

  // Si viene conversationId, traemos el hilo REAL de GHL (más preciso que la cache)
  let historial = body.historial ?? ''
  if (body.conversationId && (body.tarea === 'redactar' || body.tarea === 'resumir' || body.tarea === 'sugerir')) {
    try {
      const conn = await getConnection(user.id)
      if (conn?.private_token) {
        const auth = { token: decryptToken(conn.private_token), locationId: conn.location_id }
        const raw = await getMessages(auth, body.conversationId)
        const msgs = raw.map(toMensaje).slice().reverse()
        if (msgs.length) historial = msgs.map((m: any) => `${m.entrante ? 'Persona' : 'Yo'}: ${m.texto}`).join('\n')
      }
    } catch { /* si falla, usamos el historial que mandó el front */ }
  }

  try {
    let resultado: any
    switch (body.tarea) {
      case 'redactar':
        resultado = await redactarRespuesta({ historial, intencion: body.intencion ?? '', config })
        break
      case 'resumir':
        resultado = await resumirConversacion(historial)
        break
      case 'sugerir':
        resultado = await sugerirProximoPaso(historial)
        break
      case 'protocolo':
        resultado = await generarProtocolo(body.descripcion ?? '', me?.specialty)
        break
      default:
        return NextResponse.json({ error: 'Tarea desconocida' }, { status: 400 })
    }
    return NextResponse.json({ ok: true, resultado })
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 502 })
  }
}
