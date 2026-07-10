import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { getConnection } from '@/lib/ghl/sync'
import { decryptToken } from '@/lib/crypto'
import { sendMessage, getMessages, getConversationByContact } from '@/lib/ghl/client'
import { toMensaje } from '@/lib/ghl/normalize'

// GET  /api/ghl/mensajes?conversationId=...  → hilo de mensajes
// POST /api/ghl/mensajes  { contactId, text } → envía WhatsApp
async function auth() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return null
  const conn = await getConnection(user.id)
  if (!conn?.private_token) return null
  return { token: decryptToken(conn.private_token), locationId: conn.location_id }
}

export async function GET(req: Request) {
  const a = await auth()
  if (!a) return NextResponse.json({ error: 'Sin conexión GHL' }, { status: 401 })
  const conversationId = new URL(req.url).searchParams.get('conversationId')
  if (!conversationId) return NextResponse.json({ error: 'Falta conversationId' }, { status: 400 })
  try {
    const raw = await getMessages(a, conversationId)
    return NextResponse.json({ mensajes: raw.map(toMensaje) })
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 502 })
  }
}

export async function POST(req: Request) {
  const a = await auth()
  if (!a) return NextResponse.json({ error: 'Sin conexión GHL' }, { status: 401 })
  const { contactId, text } = await req.json()
  if (!contactId || !text?.trim()) return NextResponse.json({ error: 'Falta contactId o texto' }, { status: 400 })
  try {
    const sent = await sendMessage(a, { contactId, text: text.trim() })
    // resolver conversationId por si el front lo necesita
    let conversationId = sent.conversationId
    if (!conversationId) {
      const conv = await getConversationByContact(a, contactId)
      conversationId = conv?.id ?? null
    }
    return NextResponse.json({ ok: true, conversationId, messageId: sent.messageId ?? null })
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 502 })
  }
}
