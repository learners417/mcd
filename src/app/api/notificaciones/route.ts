import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function GET() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'No autenticado' }, { status: 401 })
  const { data } = await supabase.from('notifications')
    .select('*').order('created_at', { ascending: false }).limit(30)
  const sinLeer = (data ?? []).filter(n => !n.leida).length
  return NextResponse.json({ notificaciones: data ?? [], sinLeer })
}

export async function POST(req: Request) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'No autenticado' }, { status: 401 })
  const { id } = await req.json().catch(() => ({}))
  if (id) await supabase.from('notifications').update({ leida: true }).eq('id', id)
  else await supabase.from('notifications').update({ leida: true }).eq('leida', false)
  return NextResponse.json({ ok: true })
}
