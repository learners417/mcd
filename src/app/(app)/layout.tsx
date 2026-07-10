import Sidebar from '@/components/Sidebar'
import Campanita from '@/components/Campanita'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg)' }}>
      <Sidebar />
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '18px 40px 0' }}>
          <Campanita />
        </div>
        <div style={{ flex: 1, padding: '20px 40px 48px', maxWidth: 960 }}>{children}</div>
      </main>
    </div>
  )
}
