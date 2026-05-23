import type { MetadataRoute } from "next"
import { locales } from "@/i18n/config"
import { PUBLIC_SITE_URL } from "@/lib/env"
import { HEXAGRAM_LIBRARY } from "@/lib/hexagram-library"

export default function sitemap(): MetadataRoute.Sitemap {
  const staticRoutes = ["", "/app", "/library", "/method", "/profile"]
  const localizedStaticRoutes: MetadataRoute.Sitemap = locales.flatMap((locale) =>
    staticRoutes.map((path) => ({
      url: `${PUBLIC_SITE_URL}/${locale}${path}`,
      changeFrequency: path === "" ? "weekly" as const : "monthly" as const,
      priority: path === "" ? 1 : path === "/app" ? 0.9 : 0.7,
    })),
  )
  const hexagramRoutes: MetadataRoute.Sitemap = locales.flatMap((locale) =>
    HEXAGRAM_LIBRARY.map((entry) => ({
      url: `${PUBLIC_SITE_URL}/${locale}/hexagram/${entry.slug}`,
      changeFrequency: "monthly" as const,
      priority: 0.6,
    })),
  )

  return [
    {
      url: PUBLIC_SITE_URL,
      changeFrequency: "weekly",
      priority: 1,
    },
    ...localizedStaticRoutes,
    ...hexagramRoutes,
  ] satisfies MetadataRoute.Sitemap
}
