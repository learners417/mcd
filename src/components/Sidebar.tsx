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
  { href: '/marca',      label: 'Mi marca',   icon: '✨' },
]

export default function Sidebar() {
  const path = usePathname()
  const router = useRouter()

  async function salir() {
    await createClient().auth.signOut()
    router.push('/login')
    router.refresh()
  }

  return (
    <aside style={{ width: 220, background: 'var(--panel)', borderRight: '1px solid var(--line)', padding: '22px 16px', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28 }}>
        <div style={{ width: 30, height: 30, borderRadius: 8, background: 'linear-gradient(135deg,var(--green),var(--green-l))', display: 'grid', placeItems: 'center', fontWeight: 700, color: '#fff', fontSize: 15 }}>MC</div>
        <div><b style={{ fontSize: 15 }}>MiClínica</b><span style={{ display: 'block', fontSize: 11, color: 'var(--muted)' }}>Digital</span></div>
      </div>
      <nav style={{ flex: 1 }}>
        {NAV.map(n => {
          const on = path.startsWith(n.href)
          return (
            <Link key={n.href} href={n.href}
              style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px', borderRadius: 9, textDecoration: 'none', marginBottom: 4, fontSize: 14, color: on ? 'var(--txt)' : 'var(--muted)', background: on ? '#0c130f' : 'transparent' }}>
              <span>{n.icon}</span>{n.label}
            </Link>
          )
        })}
      </nav>
      <button onClick={salir}
        style={{ background: 'transparent', border: '1px solid var(--line)', color: 'var(--muted)', padding: '9px 12px', borderRadius: 9, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left' }}>
        ← Salir
      </button>
    </aside>
  )
}
