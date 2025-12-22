import { Link } from "@tanstack/react-router"

import { useTheme } from "@/components/theme-provider"
import { cn } from "@/lib/utils"
import icon from "/assets/images/dataset-generator-icon.png"
import iconLight from "/assets/images/dataset-generator-icon-light.png"
import logo from "/assets/images/dataset-generator-logo.png"
import logoLight from "/assets/images/dataset-generator-logo-light.png"
import title from "/assets/images/dataset-generator-title.png"
import titleLight from "/assets/images/dataset-generator-title-light.png"

interface LogoProps {
  variant?: "full" | "icon" | "responsive" | "title"
  className?: string
  asLink?: boolean
}

export function Logo({
  variant = "full",
  className,
  asLink = true,
}: LogoProps) {
  const { resolvedTheme } = useTheme()
  const isDark = resolvedTheme === "dark"

  const fullLogo = isDark ? logoLight : logo
  const iconLogo = isDark ? iconLight : icon
  const titleLogo = isDark ? titleLight : title

  const content =
    variant === "responsive" ? (
      <>
        <img
          src={titleLogo}
          alt="Dataset Generator"
          className={cn(
            "h-8 w-auto group-data-[collapsible=icon]:hidden",
            className,
          )}
        />
        <img
          src={iconLogo}
          alt="Dataset Generator"
          className={cn(
            "size-8 hidden group-data-[collapsible=icon]:block",
            className,
          )}
        />
      </>
    ) : (
      <img
        src={variant === "full" ? fullLogo : iconLogo}
        alt="Dataset Generator"
        className={cn(variant === "full" ? "h-96 w-auto" : "size-5", className)}
      />
    )

  if (!asLink) {
    return content
  }

  return <Link to="/">{content}</Link>
}
