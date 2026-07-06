'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const router = useRouter()

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setErr('')
    const supabase = createClient()
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) { setErr('Credenciales incorrectas'); return }
    router.push('/dashboard')
  }

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 20 }}>
      <form onSubmit={submit} style={{ width: '100%', maxWidth: 360, display: 'grid', gap: 10 }}>
        <div style={{ fontSize: 20, fontWeight: 600, marginBottom: 8, textAlign: 'center' }}>MiClínica Digital</div>
        <input type="email" required placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} style={inp} />
        <input type="password" required placeholder="Contraseña" value={password} onChange={e => setPassword(e.target.value)} style={inp} />
        {err && <div style={{ color: '#e06666', fontSize: 13 }}>{err}</div>}
        <button type="submit" style={btn}>Entrar</button>
      </form>
    </div>
  )
}
const inp: React.CSSProperties = { background: 'var(--panel)', border: '1px solid var(--line)', color: 'var(--txt)', padding: '12px 14px', borderRadius: 10, fontSize: 14, fontFamily: 'inherit' }
const btn: React.CSSProperties = { background: 'var(--green)', color: '#fff', border: 'none', padding: '12px', borderRadius: 10, fontSize: 15, fontWeight: 500, cursor: 'pointer' }
