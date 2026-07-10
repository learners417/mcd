import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function POST(req: Request) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'No autenticado' }, { status: 401 })
  const { title, description, steps } = await req.json()
  if (!title) return NextResponse.json({ error: 'Falta título' }, { status: 400 })
  const { data, error } = await supabase.from('protocols')
    .insert({ practitioner_id: user.id, title, description: description ?? '', steps: steps ?? [] })
    .select().single()
  if (error) return NextResponse.json({ error: error.message }, { status: 500 })
  return NextResponse.json({ ok: true, protocol: data })
}
