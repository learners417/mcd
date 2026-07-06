export default function MetricCard({ label, value, foot, tone }:{
  label: string; value: string; foot?: string; tone?: 'green' | 'gold'
}) {
  const color = tone === 'green' ? 'var(--green-l)' : tone === 'gold' ? 'var(--gold-l)' : 'var(--txt)'
  return (
    <div style={{ background: 'var(--panel)', border: '1px solid var(--line)', borderRadius: 14, padding: 18 }}>
      <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '.04em' }}>{label}</div>
      <div style={{ fontSize: 30, fontWeight: 700, lineHeight: 1, color }}>{value}</div>
      {foot && <div style={{ color: 'var(--muted)', fontSize: 12, marginTop: 8 }}>{foot}</div>}
    </div>
  )
}
