import { useState, type ImgHTMLAttributes } from 'react'
import { cn } from '@/lib/utils'

/**
 * Backend returns cover paths such as `/assets/destinations/goa.jpg`.
 * The local build ships SVG placeholders (see public/assets/README.md), so `.jpg/.png`
 * is mapped to `.svg`; if that is also missing we fall back to the generic gradient.
 */
export function resolveAsset(src: string | null | undefined): string {
  if (!src) return '/assets/destinations/generic.svg'
  if (/^https?:\/\//.test(src)) return src
  return src.replace(/\.(jpe?g|png|webp)$/i, '.svg')
}

interface Props extends Omit<ImgHTMLAttributes<HTMLImageElement>, 'src'> {
  src: string | null | undefined
}

export function CoverImage({ src, alt = '', className, ...rest }: Props) {
  const [failed, setFailed] = useState(false)
  return (
    <img
      {...rest}
      alt={alt}
      loading="lazy"
      src={failed ? '/assets/destinations/generic.svg' : resolveAsset(src)}
      onError={() => setFailed(true)}
      className={cn('object-cover', className)}
    />
  )
}
