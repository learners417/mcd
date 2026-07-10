export default function MetricCard({ label, value, foot, tone, icon }: {
  label: string; value: string; foot?: string; tone?: 'green' | 'gold'; icon?: string
}) {
  const numColor = tone === 'green' ? 'var(--green)' : tone === 'gold' ? 'var(--gold)' : 'var(--ink)'
  const icBg = tone === 'green' ? 'var(--green-bg)' : tone === 'gold' ? 'var(--gold-bg)' : '#F1F3F1'
  const icColor = tone === 'green' ? 'var(--green)' : tone === 'gold' ? 'var(--gold)' : 'var(--ink)'
  return (
    <div className="mcd-card mcd-card-pad">
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 14 }}>
        <span style={{ width: 26, height: 26, borderRadius: 8, display: 'grid', placeItems: 'center', fontSize: 13, background: icBg, color: icColor }}>{icon ?? '✦'}</span>
        <span style={{ fontSize: 12, color: 'var(--muted)', fontWeight: 500 }}>{label}</span>
      </div>
      <div style={{ fontSize: 34, fontWeight: 600, lineHeight: 1, letterSpacing: '-.02em', fontVariantNumeric: 'tabular-nums', color: numColor }}>{value}</div>
      {foot && <div style={{ fontSize: 12, color: 'var(--faint)', marginTop: 8 }}>{foot}</div>}
    </div>
  )
}
