import { useEffect } from 'react'
import {
  CircleMarker,
  MapContainer,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from 'react-leaflet'
import type { GeoJSONLineString, GeoJSONPoint, Sighting } from '../api/types'
import { getSightingName } from './format'

type MapViewProps = {
  route: GeoJSONLineString | null
  sightings: Sighting[]
}

function BoundsUpdater({ points }: { points: [number, number][] }) {
  const map = useMap()
  useEffect(() => {
    if (points.length) map.fitBounds(points, { padding: [24, 24] })
  }, [map, points])
  return null
}

function pointToLatLng(point: GeoJSONPoint): [number, number] {
  const [longitude, latitude] = point.coordinates
  return [latitude, longitude]
}

export default function MapView({ route, sightings }: MapViewProps) {
  const routePoints = route?.coordinates.map(([longitude, latitude]) => [latitude, longitude] as [number, number]) ?? []
  const locatedSightings = sightings.filter((sighting) => sighting.location)
  const bounds = [
    ...routePoints,
    ...locatedSightings.map((sighting) => pointToLatLng(sighting.location!)),
  ]
  const center = bounds[0] ?? [53.38, -1.87]
  if (!routePoints.length && !locatedSightings.length) return null

  return (
    <div className="map-wrap">
      <MapContainer center={center} zoom={12} scrollWheelZoom={false}>
        <BoundsUpdater points={bounds} />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {routePoints.length > 1 && <Polyline positions={routePoints} pathOptions={{ color: '#2e7049', weight: 4 }} />}
        {locatedSightings.map((sighting) => {
          const name = getSightingName(sighting)
          return (
            <CircleMarker
              center={pointToLatLng(sighting.location!)}
              key={sighting.id}
              radius={8}
              pathOptions={{ color: '#fff', weight: 2, fillColor: '#b87932', fillOpacity: 1 }}
            >
              <Popup>{name.common} · {sighting.verification.status}</Popup>
            </CircleMarker>
          )
        })}
      </MapContainer>
    </div>
  )
}
