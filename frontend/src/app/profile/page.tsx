import { redirect } from "next/navigation"

export default function LegacyProfileRedirectPage() {
  redirect("/en/profile")
}
