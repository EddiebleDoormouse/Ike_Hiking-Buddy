import { useEffect, useState, type ReactNode } from 'react'
import type { GeoJSONLineString } from '../api/types'

/** Number of masonry columns for the current window width. */
function columnsFor(width: number): number {
  if (width >= 1180) return 4
  if (width >= 820) return 3
  return 2
}

export function useColumnCount(): number {
  const [count, setCount] = useState(() => columnsFor(window.innerWidth))
  useEffect(() => {
    const onResize = () => setCount(columnsFor(window.innerWidth))
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  return count
}

export type BoardEntry = {
  key: string
  /** Rough height relative to the column width, used to balance columns. */
  weight: number
  node: ReactNode
}

/**
 * Masonry board: items keep reading order left-to-right, each one going
 * into the currently shortest column (like a pinboard).
 */
export function Masonry({ items }: { items: BoardEntry[] }) {
  const count = useColumnCount()
  const columns: BoardEntry[][] = Array.from({ length: count }, () => [])
  const heights = Array.from({ length: count }, () => 0)
  for (const item of items) {
    const target = heights.indexOf(Math.min(...heights))
    columns[target].push(item)
    heights[target] += item.weight + 0.12
  }
  return (
    <div className="masonry" style={{ gridTemplateColumns: `repeat(${count}, minmax(0, 1fr))` }}>
      {columns.map((column, index) => (
        <div className="masonry-col" key={index}>
          {column.map((item) => <div className="masonry-item" key={item.key}>{item.node}</div>)}
        </div>
      ))}
    </div>
  )
}

/** The route drawn like a footpath on a contour map. Pure SVG, no tiles. */
export function RouteTrace({ route, className = '' }: { route: GeoJSONLineString | null; className?: string }) {
  const coords = route?.coordinates ?? []
  const width = 400
  const height = 300
  let path = ''
  let start: [number, number] | null = null
  let end: [number, number] | null = null
  if (coords.length > 1) {
    const midLat = coords.reduce((sum, [, lat]) => sum + lat, 0) / coords.length
    const scaleX = Math.cos((midLat * Math.PI) / 180)
    const xs = coords.map(([lon]) => lon * scaleX)
    const ys = coords.map(([, lat]) => lat)
    const minX = Math.min(...xs), maxX = Math.max(...xs)
    const minY = Math.min(...ys), maxY = Math.max(...ys)
    const span = Math.max(maxX - minX, maxY - minY) || 1
    const pad = 46
    const scale = Math.min((width - pad * 2) / Math.max(maxX - minX, span * 0.2), (height - pad * 2) / Math.max(maxY - minY, span * 0.2))
    const offsetX = (width - (maxX - minX) * scale) / 2
    const offsetY = (height - (maxY - minY) * scale) / 2
    const points = xs.map((x, index) => [
      offsetX + (x - minX) * scale,
      height - (offsetY + (ys[index] - minY) * scale),
    ] as [number, number])
    path = points.map(([x, y], index) => `${index ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ')
    start = points[0]
    end = points[points.length - 1]
  }
  return (
    <svg className={`route-trace ${className}`} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Route outline">
      <g className="contours" fill="none">
        {[0, 1, 2, 3, 4, 5, 6].map((ring) => (
          <ellipse key={ring} cx={250} cy={170} rx={40 + ring * 34} ry={26 + ring * 24} transform={`rotate(-14 250 170)`} />
        ))}
        {[0, 1, 2].map((ring) => (
          <ellipse key={`b${ring}`} cx={70} cy={60} rx={30 + ring * 26} ry={20 + ring * 18} />
        ))}
      </g>
      {path ? (
        <>
          <path className="route-halo" d={path} />
          <path className="route-line" d={path} />
          {start && <circle className="route-start" cx={start[0]} cy={start[1]} r={6} />}
          {end && (end[0] !== start?.[0] || end[1] !== start?.[1]) && <circle className="route-end" cx={end[0]} cy={end[1]} r={5} />}
        </>
      ) : (
        <text x={width / 2} y={height / 2} textAnchor="middle" className="route-empty">No track yet</text>
      )}
    </svg>
  )
}

/** Deterministic little waveform so each recording card looks distinct. */
export function Waveform({ seed, bars = 36 }: { seed: string; bars?: number }) {
  let hash = 0
  for (const char of seed) hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  const heights = Array.from({ length: bars }, (_, index) => {
    hash = (hash * 1103515245 + 12345) >>> 0
    const envelope = Math.sin((index / (bars - 1)) * Math.PI) * 0.7 + 0.3
    return Math.max(0.12, ((hash % 1000) / 1000) * envelope)
  })
  return (
    <div className="waveform" aria-hidden="true">
      {heights.map((value, index) => <span key={index} style={{ height: `${Math.round(value * 100)}%` }} />)}
    </div>
  )
}
