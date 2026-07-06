import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { syncPractitioner } from '@/lib/ghl/sync'

export async function POST(req: Request) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'No autenticado' }, { status: 401 })

  const force = new URL(req.url).searchParams.get('force') === '1'
  const result = await syncPractitioner(user.id, force)
  return NextResponse.json(result, { status: result.ok ? 200 : 207 })
}
