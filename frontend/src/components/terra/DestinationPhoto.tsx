import type { TerraPhoto } from '@/lib/terra'

type Props = {
  photo?: TerraPhoto | null
  className?: string
  sizes?: string
  priority?: boolean
}

export function DestinationPhoto({ photo, className = '', sizes, priority = false }: Props) {
  if (!photo?.url) {
    return (
      <div className={`grid place-items-center bg-[color:var(--terra-forest)] text-[color:var(--terra-ivory)] ${className}`} aria-hidden>
        <span className="px-4 text-center text-xs opacity-80">No licensed photograph in this snapshot</span>
      </div>
    )
  }
  return (
    <figure className={`relative overflow-hidden ${className}`}>
      <img
        src={photo.url}
        alt={photo.alt || 'Destination photograph'}
        className="size-full object-cover"
        loading={priority ? 'eager' : 'lazy'}
        decoding="async"
        sizes={sizes}
      />
      {(photo.attribution || photo.license_name) && (
        <figcaption className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent px-3 pb-2 pt-8 text-[10px] leading-snug text-white">
          {[photo.author, photo.license_name].filter(Boolean).join(' · ')}
        </figcaption>
      )}
    </figure>
  )
}
