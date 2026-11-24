import { useEffect, useRef, useState } from 'react'
import maplibregl, { type Map as MapLibreMap, type GeoJSONSource } from 'maplibre-gl'
import type { FeatureCollection } from 'geojson'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { TerraDestination } from '@/lib/terra'

type Props = {
  items: Array<TerraDestination & { lat: number; lon: number }>
  selectedSlug?: string | null
  onSelect?: (slug: string) => void
  className?: string
}

const EMPTY: FeatureCollection = { type: 'FeatureCollection', features: [] }

export function DestinationMap({ items, selectedSlug, onSelect, className = '' }: Props) {
  const host = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!host.current || mapRef.current) return
    let cancelled = false
    const map = new maplibregl.Map({
      container: host.current,
      style: {
        version: 8,
        sources: {
          india: { type: 'geojson', data: EMPTY },
          pins: { type: 'geojson', data: EMPTY },
        },
        layers: [
          { id: 'background', type: 'background', paint: { 'background-color': '#efeae0' } },
          {
            id: 'india-fill',
            type: 'fill',
            source: 'india',
            paint: { 'fill-color': '#a5b4a0', 'fill-opacity': 0.55 },
          },
          {
            id: 'india-line',
            type: 'line',
            source: 'india',
            paint: { 'line-color': '#243e36', 'line-width': 1.2 },
          },
          {
            id: 'pins-circle',
            type: 'circle',
            source: 'pins',
            paint: {
              'circle-radius': ['case', ['boolean', ['get', 'selected'], false], 8, 5.5],
              'circle-color': ['case', ['boolean', ['get', 'selected'], false], '#bb7955', '#243e36'],
              'circle-stroke-width': 1.5,
              'circle-stroke-color': '#f6f3eb',
            },
          },
          {
            id: 'pins-label',
            type: 'symbol',
            source: 'pins',
            layout: {
              'text-field': ['get', 'name'],
              'text-size': 11,
              'text-offset': [0, 1.2],
              'text-anchor': 'top',
              'text-optional': true,
            },
            paint: { 'text-color': '#222722', 'text-halo-color': '#f6f3eb', 'text-halo-width': 1.2 },
          },
        ],
      },
      center: [82, 22],
      zoom: 3.6,
      attributionControl: false,
      cooperativeGestures: true,
    })
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.addControl(
      new maplibregl.AttributionControl({
        compact: true,
        customAttribution: 'Basemap: simplified local outline · Pins: stored destination coordinates · © OpenStreetMap contributors where OSM-derived',
      }),
    )
    map.on('error', () => setFailed(true))
    map.on('load', async () => {
      try {
        const outline = await fetch('/geo/india-outline.json').then((res) => {
          if (!res.ok) throw new Error('outline missing')
          return res.json()
        })
        if (cancelled) return
        ;(map.getSource('india') as GeoJSONSource).setData(outline)
      } catch {
        if (!cancelled) setFailed(true)
      }
    })
    map.on('click', 'pins-circle', (event) => {
      const slug = event.features?.[0]?.properties?.slug
      if (typeof slug === 'string') onSelect?.(slug)
    })
    map.on('mouseenter', 'pins-circle', () => {
      map.getCanvas().style.cursor = 'pointer'
    })
    map.on('mouseleave', 'pins-circle', () => {
      map.getCanvas().style.cursor = ''
    })
    mapRef.current = map
    return () => {
      cancelled = true
      map.remove()
      mapRef.current = null
    }
  }, [onSelect])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    const update = () => {
      const source = map.getSource('pins') as GeoJSONSource | undefined
      if (!source) return
      source.setData({
        type: 'FeatureCollection',
        features: items.map((item) => ({
          type: 'Feature',
          properties: {
            slug: item.slug,
            name: item.name,
            selected: item.slug === selectedSlug,
          },
          geometry: { type: 'Point', coordinates: [item.lon, item.lat] },
        })),
      })
      if (items.length) {
        const bounds = new maplibregl.LngLatBounds()
        items.forEach((item) => bounds.extend([item.lon, item.lat]))
        map.fitBounds(bounds, { padding: 48, maxZoom: 6.5, duration: 600 })
      }
    }
    if (map.isStyleLoaded()) update()
    else map.once('load', update)
  }, [items, selectedSlug])

  if (failed) {
    return (
      <div className={`rounded-[1.5rem] border border-line bg-surface-2 p-4 text-sm text-muted ${className}`} role="status">
        The interactive map could not start. Use the destination list instead. Coordinates are still available on each place page.
      </div>
    )
  }

  return <div ref={host} className={`overflow-hidden rounded-[1.5rem] border border-line ${className}`} role="region" aria-label="Destination map" />
}
