import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import { AppProviders } from "@/components/providers/app-providers"
import "./globals.css"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: "I Ching Studio",
  description: "Modern divination studio powered by FastAPI + Next.js",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="zh-Hans" suppressHydrationWarning>
      <body className={`${geistSans.variable} ${geistMono.variable} min-h-screen bg-background text-foreground`}>
        <AppProviders>
          <div className="relative min-h-screen bg-app-radial bg-cover bg-fixed bg-center">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.08),_transparent_55%)]" />
            <div className="relative z-10 min-h-screen">{children}</div>
          </div>
        </AppProviders>
      </body>
    </html>
  )
}
