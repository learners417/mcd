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
    e.preventDefault(); setErr('')
    const { error } = await createClient().auth.signInWithPassword({ email, password })
    if (error) { setErr('Correo o contraseña incorrectos'); return }
    router.push('/dashboard')
  }
  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 20, background: 'var(--bg)' }}>
      <form onSubmit={submit} style={{ width: '100%', maxWidth: 380 }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: 28 }}>
          <div style={{ width: 52, height: 52, borderRadius: 15, background: 'linear-gradient(140deg,var(--green),var(--green-l))', display: 'grid', placeItems: 'center', color: '#fff', fontWeight: 700, fontSize: 20, boxShadow: '0 6px 18px rgba(61,107,79,.28)', marginBottom: 14 }}>MC</div>
          <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-.01em' }}>MiClínica Digital</div>
          <div className="mcd-sub" style={{ marginTop: 4 }}>Tu consultorio, en un solo lugar.</div>
        </div>
        <div className="mcd-card mcd-card-pad" style={{ display: 'grid', gap: 12 }}>
          <input type="email" required placeholder="Correo" value={email} onChange={e => setEmail(e.target.value)} className="mcd-input" />
          <input type="password" required placeholder="Contraseña" value={password} onChange={e => setPassword(e.target.value)} className="mcd-input" />
          {err && <div style={{ color: 'var(--danger)', fontSize: 13 }}>{err}</div>}
          <button type="submit" className="mcd-btn" style={{ marginTop: 2 }}>Entrar</button>
        </div>
      </form>
    </div>
  )
}
