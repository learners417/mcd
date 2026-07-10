'use client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'

const NAV = [
  { href: '/dashboard',  label: 'Hoy',        icon: '☀️' },
  { href: '/personas',   label: 'Personas',   icon: '💬' },
  { href: '/pacientes',  label: 'Pacientes',  icon: '👥' },
  { href: '/protocolos', label: 'Protocolos', icon: '📋' },
  { href: '/agenda',     label: 'Agenda',     icon: '📅' },
  { href: '/cobros',     label: 'Cobros',     icon: '💰' },
  { href: '/asistente',  label: 'Asistente',  icon: '✨' },
  { href: '/marca',      label: 'Mi marca',   icon: '⚙️' },
]

export default function Sidebar() {
  const path = usePathname()
  const router = useRouter()
  async function salir() {
    await createClient().auth.signOut()
    router.push('/login'); router.refresh()
  }
  return (
    <aside style={{ width: 236, background: 'var(--card)', borderRight: '1px solid var(--line)', padding: '26px 18px', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 11, marginBottom: 34, padding: '0 6px' }}>
        <div style={{ width: 36, height: 36, borderRadius: 11, background: 'linear-gradient(140deg,var(--green),var(--green-l))', display: 'grid', placeItems: 'center', color: '#fff', fontWeight: 700, fontSize: 15, boxShadow: '0 4px 12px rgba(61,107,79,.25)' }}>MC</div>
        <div><b style={{ fontSize: 15, fontWeight: 600, letterSpacing: '-.01em' }}>MiClínica</b><span style={{ display: 'block', fontSize: 11, color: 'var(--faint)' }}>Digital</span></div>
      </div>
      <nav style={{ flex: 1 }}>
        {NAV.map(n => {
          const on = path.startsWith(n.href)
          return (
            <Link key={n.href} href={n.href}
              style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '11px 13px', borderRadius: 11, textDecoration: 'none', marginBottom: 3, fontSize: 14, color: on ? 'var(--green)' : 'var(--muted)', background: on ? 'var(--green-bg)' : 'transparent', fontWeight: on ? 500 : 400 }}>
              <span style={{ width: 18, textAlign: 'center', opacity: on ? 1 : .7 }}>{n.icon}</span>{n.label}
            </Link>
          )
        })}
      </nav>
      <button onClick={salir} className="mcd-btn-ghost" style={{ textAlign: 'left', marginTop: 'auto' }}>← Salir</button>
    </aside>
  )
}
