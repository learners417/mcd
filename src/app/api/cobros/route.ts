import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

// multipart/form-data: amount_usd, concept, patient_id (opcional), receipt (file OBLIGATORIO)
// Misma lógica de evidencia que los cinturones: sin comprobante no hay cobro.
export async function POST(req: Request) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return NextResponse.json({ error: 'No autenticado' }, { status: 401 })

  const form = await req.formData()
  const amount = Number(form.get('amount_usd'))
  const concept = String(form.get('concept') ?? '')
  const patientId = form.get('patient_id') ? String(form.get('patient_id')) : null
  const receipt = form.get('receipt') as File | null

  if (!amount || amount <= 0) return NextResponse.json({ error: 'Monto inválido' }, { status: 400 })
  if (!receipt) return NextResponse.json({ error: 'El comprobante es obligatorio' }, { status: 400 })
  if (receipt.size > 8 * 1024 * 1024) return NextResponse.json({ error: 'Comprobante muy pesado (máx 8MB)' }, { status: 400 })

  // 1) subir el screenshot al bucket privado, carpeta del sanador
  const ext = (receipt.name.split('.').pop() || 'png').toLowerCase()
  const path = `${user.id}/${Date.now()}.${ext}`
  const { error: upErr } = await supabase.storage
    .from('comprobantes')
    .upload(path, receipt, { contentType: receipt.type || 'image/png' })
  if (upErr) return NextResponse.json({ error: `No se pudo subir el comprobante: ${upErr.message}` }, { status: 500 })

  // 2) registrar el cobro
  const { data, error } = await supabase.from('cobros').insert({
    practitioner_id: user.id,
    patient_id: patientId,
    amount_usd: amount,
    concept,
    receipt_path: path,
  }).select().single()
  if (error) return NextResponse.json({ error: error.message }, { status: 500 })

  return NextResponse.json({ ok: true, cobro: data })
}
