import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import { AppProviders } from "@/components/providers/app-providers"
import { ThemeToggle } from "@/components/theme/theme-toggle"
import Script from "next/script"
import "./globals.css"

const CRYSTAL_BALL_FAVICON =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ctext y='55%25' x='50%25' text-anchor='middle' dominant-baseline='middle' font-size='48'%3E%F0%9F%94%AE%3C/text%3E%3C/svg%3E"

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
  icons: {
    icon: CRYSTAL_BALL_FAVICON,
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="zh-Hans" suppressHydrationWarning>
      <head>
        <Script src="https://www.googletagmanager.com/gtag/js?id=G-FGD47JMEXQ" strategy="afterInteractive" />
        <Script id="ga-gtag" strategy="afterInteractive">
          {`
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', 'G-FGD47JMEXQ');
          `}
        </Script>
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} min-h-screen bg-background text-foreground`}>
        <AppProviders>
          <div className="relative min-h-screen bg-app-radial bg-cover bg-fixed bg-center">
            <div className="app-overlay absolute inset-0 pointer-events-none" />
            <div className="absolute right-6 top-6 z-20 flex items-center gap-2">
              <ThemeToggle />
            </div>
            <div className="relative z-10 min-h-screen">{children}</div>
          </div>
        </AppProviders>
      </body>
    </html>
  )
}
