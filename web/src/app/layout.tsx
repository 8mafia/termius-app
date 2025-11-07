import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'ParSSH - SSH Manager',
  description: 'A powerful SSH client and terminal manager',
  keywords: ['ssh', 'terminal', 'client', 'manager', 'remote', 'server'],
  authors: [{ name: 'ParSSH Team' }],
  viewport: 'width=device-width, initial-scale=1',
  themeColor: '#3b82f6',
  manifest: '/manifest.json',
  icons: {
    icon: '/favicon.ico',
    apple: '/apple-touch-icon.png',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="h-full">
      <body className={inter.className}>
        <div className="min-h-full bg-gray-50">
          {children}
        </div>
      </body>
    </html>
  )
}