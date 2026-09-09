import type { Metadata } from "next"
import { SpeedInsights } from "@vercel/speed-insights/next"
import { Analytics } from "@vercel/analytics/next"
import { Geist, Geist_Mono } from "next/font/google"
import { AppProviders } from "@/components/providers/app-providers"
import { PUBLIC_SITE_URL } from "@/lib/env"
import Script from "next/script"
import "./globals.css"
import "./autumn.css"

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  metadataBase: new URL(PUBLIC_SITE_URL),
  title: "I Ching Studio",
  description: "A bilingual I Ching divination platform for casting, interpretation, classical evidence, and verification.",
  alternates: {
    canonical: "/",
    languages: {
      en: "/en",
      zh: "/zh",
    },
  },
  openGraph: {
    title: "I Ching Studio",
    description: "A bilingual I Ching divination platform for casting, interpretation, classical evidence, and verification.",
    url: PUBLIC_SITE_URL,
    siteName: "I Ching Studio",
    type: "website",
  },
  icons: {
    icon: "/autumn/ginkgo-leaf.webp",
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
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
      <body className={`${geistSans.variable} ${geistMono.variable} autumn-app min-h-screen bg-background text-foreground`}>
        <AppProviders>
          {children}
        </AppProviders>
        <SpeedInsights />
        <Analytics />
      </body>
    </html>
  )
}
