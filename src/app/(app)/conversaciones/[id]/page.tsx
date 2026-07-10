import { createClient } from '@/lib/supabase/server'
import { notFound } from 'next/navigation'
import ChatView from './ChatView'

export const dynamic = 'force-dynamic'

// searchParams y params compatibles con Next 14 (objeto) y 15 (Promise):
// await sobre un no-Promise devuelve el mismo valor → seguro en ambos.
export default async function ConversacionPage(props: any) {
  const { id } = await props.params
  const sp = props.searchParams ? await props.searchParams : {}
  const nombre = sp?.nombre
  let cid = sp?.contactId

  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!cid) {
    const { data: c } = await supabase.from('ghl_cache')
      .select('payload').eq('practitioner_id', user?.id).eq('resource', 'conversations').maybeSingle()
    const conv = ((c?.payload as any[]) ?? []).find(x => x.id === id)
    cid = conv?.contactId
  }
  if (!cid) return notFound()

  return <ChatView conversationId={id} contactId={cid} nombre={nombre || 'Conversación'} />
}
