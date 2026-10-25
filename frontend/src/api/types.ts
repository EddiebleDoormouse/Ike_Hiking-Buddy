// Mirrors backend models; when docs/openapi.json lands on main, align with it — the backend wins on any mismatch.
export type GeoJSONLineString = {
  type: 'LineString'
  coordinates: [number, number][]
}

export type GeoJSONPoint = {
  type: 'Point'
  coordinates: [number, number]
}

export type HikeCreate = {
  title: string
  trail_name: string
  hiker: string
  date: string
  status: 'planned' | 'completed'
  based_on_hike_id?: string | null
}

export type Candidate = {
  common_name: string
  scientific_name: string
  confidence: number
  group: string
}

export type SpecialistResult = {
  source: 'plantnet' | 'mushroom_id'
  top_name: string
  top_common_name: string | null
  top_score: number
  alternatives: { name: string; common_name: string | null; score: number }[]
  gbif_key: number | null
}

export type Verification = {
  status: 'confirmed' | 'plausible' | 'unsure' | 'not_applicable'
  chosen: Candidate | null
  gbif_nearby_count: number | null
  gbif_key: number | null
  specialist: SpecialistResult | null
  specialist_agrees: 'species' | 'genus' | 'no' | null
  reasons: string[]
}

export type PlanDraft = {
  summary_md: string
  start_time_local: string
  est_duration_min: number
  kit: { item: string; reason: string; done: boolean }[]
  hazards: { text: string; source_url: string | null; source_title: string | null }[]
  notes: string[]
}

export type Check = {
  name: string
  passed: boolean
  detail: string
}

export type Plan = {
  final: PlanDraft
  iterations: { draft: PlanDraft; checks: Check[] }[]
  revisions: number
  what_you_might_see: { name: string; scientific_name: string; count: number }[]
  leave_by: string
  forecast_summary?: string
}

export type HikeStats = {
  distance_km: number | null
  duration_s: number | null
  moving_s: number | null
  ascent_m: number | null
  descent_m: number | null
  avg_hr: number | null
  max_hr: number | null
  start_time: string | null
  end_time: string | null
  avg_moving_speed_kmh: number | null
}

export type Hike = HikeCreate & {
  id: string
  route: GeoJSONLineString | null
  start: GeoJSONPoint | null
  stats: HikeStats | null
  pace_factor: number | null
  plan: Plan | null
  recap_md: string | null
  created_at: string
}

export type HikeCard = {
  id: string
  title: string
  trail_name: string
  hiker: string
  date: string
  status: 'planned' | 'completed'
  cover_media_id: string | null
  distance_km: number | null
  ascent_m: number | null
  species_count: number | null
}

export type MediaItem = {
  id: string
  hike_id: string
  kind: 'photo' | 'audio' | 'video' | 'note'
  filename: string
  mime: string
  original_file_id: string | null
  display_file_id: string | null
  thumb_file_id: string | null
  taken_at: string | null
  location: GeoJSONPoint | null
  location_source: string | null
  caption: string | null
  tags: string[]
  text: string | null
  created_at: string
}

export type Sighting = {
  id: string
  hike_id: string
  media_id: string
  candidates: Candidate[]
  verification: Verification
  location: GeoJSONPoint | null
  seen_at: string | null
  safety_note: string | null
}

export type HikeDetail = {
  hike: Hike
  media: MediaItem[]
  sightings: Sighting[]
}

export type SearchResult = {
  media: MediaItem
  hike_title: string
  sighting: Sighting | null
  score: number
}

export type Health = {
  ok: boolean
  mongo: boolean
}

export type UploadMediaResponse = {
  media: MediaItem
  sighting: Sighting | null
}

export type TrackUploadResponse = {
  stats: HikeStats
  route: GeoJSONLineString
}

export type RecapResponse = {
  recap_md: string
}
