import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'MiClínica Digital',
  description: 'Tu consultorio digital, en un solo lugar.',
  manifest: '/manifest.json',
  appleWebApp: { capable: true, statusBarStyle: 'black-translucent', title: 'MiClínica' },
}

export const viewport = {
  themeColor: '#3D6B4F',
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body>{children}</body>
    </html>
  )
}
