// ============================================================================
//  MCD · Motor de IA · Proxy OpenAI-compatible (server-only)
//  Timeout 20s + 1 reintento. Si el proxy tarda o falla, la UI recibe error
//  claro en vez de colgarse.
// ============================================================================

const PROXY_URL = process.env.AI_PROXY_URL
  ?? 'https://apighl.vercel.app/api/v1/chat/completions'
const MODEL = process.env.AI_MODEL ?? 'gpt-4o-mini'
const TIMEOUT = 20_000

export async function chat(
  messages: { role: string; content: string }[],
  opts?: { temperature?: number },
  attempt = 0
): Promise<string> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT)
  try {
    const res = await fetch(PROXY_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: MODEL, messages, temperature: opts?.temperature ?? 0.6, max_tokens: 700 }),
      cache: 'no-store',
      signal: ctrl.signal,
    })
    if ((res.status === 429 || res.status >= 500) && attempt < 1) {
      await new Promise(r => setTimeout(r, 800))
      return chat(messages, opts, attempt + 1)
    }
    if (!res.ok) throw new Error(`IA ${res.status}`)
    const data = await res.json()
    const out = data.choices?.[0]?.message?.content
    if (!out) throw new Error('La IA devolvió una respuesta vacía')
    return out
  } catch (e: any) {
    if (e.name === 'AbortError') {
      if (attempt < 1) return chat(messages, opts, attempt + 1)
      throw new Error('La IA tardó demasiado. Probá de nuevo.')
    }
    throw e
  } finally {
    clearTimeout(timer)
  }
}
