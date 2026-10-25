import { notifyApiError } from './errors'
import { asHikeDetail, createMockHike, mockState } from './mocks'
import type {
  Candidate,
  Health,
  Hike,
  HikeCard,
  HikeCreate,
  HikeDetail,
  HikeStats,
  MediaItem,
  MediaVariant,
  Plan,
  RecapResponse,
  SearchResult,
  Sighting,
  SpeciesNear,
  TrackUploadResponse,
  UploadMediaResponse,
} from './types'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === 'true'

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds))
}

function describeDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  // FastAPI 422 responses return a list of {loc, msg, type} entries.
  if (Array.isArray(detail)) {
    return detail
      .map((entry) => (entry && typeof entry === 'object' && 'msg' in entry ? String(entry.msg) : ''))
      .filter(Boolean)
      .join('; ')
  }
  return ''
}

export function friendlyApiError(status: number, detail: string): string {
  const notReady = detail.match(/^not implemented yet \((.+)\)$/)
  if (status === 501) {
    return `This part of the API isn't ready yet${notReady ? ` (${notReady[1]})` : ''}.`
  }
  if (status === 404) return detail || 'Not found.'
  if (detail) return `Request failed (${status}): ${detail}`
  if (status >= 500) return `The server hit an error (${status}). Please try again.`
  return `Request failed (${status}).`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, init)
  } catch {
    const message = `Could not reach the API at ${API_URL}. Is the backend running?`
    notifyApiError(message)
    throw new Error(message)
  }
  if (!response.ok) {
    let detail = ''
    try {
      const payload: { detail?: unknown } = await response.json()
      detail = describeDetail(payload.detail)
    } catch {
      detail = ''
    }
    const message = friendlyApiError(response.status, detail)
    notifyApiError(message)
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

function toCard(hike: Hike): HikeCard {
  const cover = mockState.media.find((media) => media.hike_id === hike.id && media.kind === 'photo')
  return {
    id: hike.id,
    title: hike.title,
    trail_name: hike.trail_name,
    hiker: hike.hiker,
    date: hike.date,
    status: hike.status,
    cover_media_id: cover?.id ?? null,
    distance_km: hike.stats?.distance_km ?? null,
    ascent_m: hike.stats?.ascent_m ?? null,
    species_count: mockState.sightings.filter(
      (sighting) => sighting.hike_id === hike.id
        && sighting.verification.status !== 'not_applicable'
        && sighting.verification.chosen !== null,
    ).length,
  }
}

export async function getHealth(): Promise<Health> {
  if (USE_MOCKS) {
    await sleep(600)
    return { ok: true, mongo: true }
  }
  return request<Health>('/health')
}

export async function listHikes(): Promise<HikeCard[]> {
  if (USE_MOCKS) {
    await sleep(600)
    return mockState.hikes.map(toCard)
  }
  return request<HikeCard[]>('/hikes')
}

export async function getHike(id: string): Promise<HikeDetail> {
  if (USE_MOCKS) {
    await sleep(600)
    const hike = mockState.hikes.find((item) => item.id === id)
    if (!hike) throw new Error('Hike not found. It may have been removed.')
    return asHikeDetail(hike)
  }
  return request<HikeDetail>(`/hikes/${encodeURIComponent(id)}`)
}

export async function getMedia(id: string): Promise<MediaItem> {
  if (USE_MOCKS) {
    await sleep(300)
    const media = mockState.media.find((item) => item.id === id)
    if (!media) throw new Error('Media not found.')
    return media
  }
  return request<MediaItem>(`/media/${encodeURIComponent(id)}`)
}

export async function createHike(body: HikeCreate): Promise<Hike> {
  if (USE_MOCKS) {
    await sleep(600)
    return createMockHike(body)
  }
  return request<Hike>('/hikes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export type UploadProgress = {
  percent: number
  stage: 'uploading' | 'analysing'
}

function uploadWithProgress(
  hikeId: string,
  file: File,
  onProgress?: (progress: UploadProgress) => void,
): Promise<UploadMediaResponse> {
  return new Promise((resolve, reject) => {
    const fail = (message: string) => {
      notifyApiError(message)
      reject(new Error(message))
    }
    const form = new FormData()
    form.append('file', file)
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_URL}/hikes/${encodeURIComponent(hikeId)}/media`)
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress?.({ percent: Math.round((event.loaded / event.total) * 100), stage: 'uploading' })
      }
    }
    xhr.upload.onload = () => onProgress?.({ percent: 100, stage: 'analysing' })
    xhr.onerror = () => fail('Upload failed. Check your connection and try again.')
    xhr.onload = () => {
      if (xhr.status < 200 || xhr.status >= 300) {
        let detail = ''
        try {
          const payload = JSON.parse(xhr.responseText) as { detail?: unknown }
          detail = describeDetail(payload.detail)
        } catch {
          detail = ''
        }
        fail(friendlyApiError(xhr.status, detail) || `Upload failed (${xhr.status}).`)
        return
      }
      try {
        resolve(JSON.parse(xhr.responseText) as UploadMediaResponse)
      } catch {
        fail('The server returned an unreadable upload response.')
      }
    }
    xhr.send(form)
  })
}

export async function uploadMedia(
  hikeId: string,
  file: File,
  onProgress?: (progress: UploadProgress) => void,
): Promise<UploadMediaResponse> {
  if (!USE_MOCKS) return uploadWithProgress(hikeId, file, onProgress)
  const objectUrl = URL.createObjectURL(file)
  const id = `media-upload-${Date.now()}`
  mockState.objectUrls.set(id, objectUrl)
  for (const percent of [15, 38, 64, 86, 100]) {
    await sleep(120)
    onProgress?.({ percent, stage: 'uploading' })
  }
  await sleep(400)
  onProgress?.({ percent: 100, stage: 'analysing' })
  await sleep(500)
  const media: MediaItem = {
    id,
    hike_id: hikeId,
    kind: file.type.startsWith('image/') ? 'photo' : 'audio',
    filename: file.name,
    mime: file.type || 'application/octet-stream',
    original_file_id: id,
    display_file_id: id,
    thumb_file_id: id,
    taken_at: null,
    location: null,
    location_source: null,
    caption: file.type.startsWith('image/') ? 'New photo from your hike' : 'New audio recording',
    tags: ['new upload'],
    text: null,
    created_at: new Date().toISOString(),
  }
  const candidate: Candidate = {
    common_name: 'Common Buzzard',
    scientific_name: 'Buteo buteo',
    confidence: 0.61,
    group: 'bird',
  }
  const sighting: Sighting = {
    id: `sighting-upload-${Date.now()}`,
    hike_id: hikeId,
    media_id: id,
    candidates: [candidate],
    verification: {
      status: 'plausible',
      chosen: candidate,
      gbif_nearby_count: 4,
      gbif_key: 2480583,
      specialist: null,
      specialist_agrees: null,
      reasons: [
        'This is a plausible suggestion at 61% confidence.',
        'Four nearby seasonal records were found.',
        'A specialist second opinion is not available for this upload.',
      ],
    },
    location: null,
    seen_at: null,
    safety_note: null,
  }
  mockState.media.unshift(media)
  mockState.sightings.unshift(sighting)
  return { media, sighting }
}

export async function uploadTrack(hikeId: string, file: File): Promise<TrackUploadResponse> {
  if (USE_MOCKS) {
    await sleep(600)
    void file
    const hike = mockState.hikes.find((item) => item.id === hikeId)
    if (!hike) throw new Error('Hike not found.')
    const route = {
      type: 'LineString' as const,
      coordinates: [
        [-1.87, 53.38],
        [-1.88, 53.39],
        [-1.86, 53.4],
        [-1.87, 53.38],
      ] as [number, number][],
    }
    const stats: HikeStats = {
      distance_km: 8.2,
      duration_s: 14400,
      moving_s: 12300,
      ascent_m: 320,
      descent_m: 310,
      avg_hr: null,
      max_hr: null,
      start_time: null,
      end_time: null,
      avg_moving_speed_kmh: 2.4,
    }
    hike.route = route
    hike.stats = stats
    return { route, stats }
  }
  const form = new FormData()
  form.append('file', file)
  return request<TrackUploadResponse>(`/hikes/${encodeURIComponent(hikeId)}/track`, {
    method: 'POST',
    body: form,
  })
}

export async function planHike(hikeId: string): Promise<Plan> {
  if (USE_MOCKS) {
    await sleep(600)
    const hike = mockState.hikes.find((item) => item.id === hikeId)
    if (!hike) throw new Error('Hike not found.')
    const template = mockState.hikes.find((item) => item.id === 'hike-kinder-planned')?.plan
    if (!template) throw new Error('The mock plan is not available.')
    hike.plan = template
    return hike.plan
  }
  return request<Plan>(`/hikes/${encodeURIComponent(hikeId)}/plan`, { method: 'POST' })
}

export async function recap(hikeId: string): Promise<RecapResponse> {
  if (USE_MOCKS) {
    await sleep(600)
    const hike = mockState.hikes.find((item) => item.id === hikeId)
    if (!hike) throw new Error('Hike not found.')
    hike.recap_md = `## A day outside\n\n${hike.title} covered **${hike.stats?.distance_km ?? 'a winding route'} km** through the hills. The folder keeps the photographs, track and wildlife notes together.\n\nConditions and identifications are uncertain; use this recap as a memory aid, not a record of certainty.`
    return { recap_md: hike.recap_md }
  }
  return request<RecapResponse>(`/hikes/${encodeURIComponent(hikeId)}/recap`, { method: 'POST' })
}

function searchableText(result: SearchResult): string {
  const names = result.sighting?.candidates
    .flatMap((candidate) => [candidate.common_name, candidate.scientific_name])
    .join(' ')
  return [
    result.media.caption,
    result.media.tags.join(' '),
    result.hike_title,
    names,
    result.sighting?.verification.chosen?.common_name,
    result.sighting?.verification.chosen?.scientific_name,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
}

export async function search(q: string, hikeId?: string): Promise<SearchResult[]> {
  if (USE_MOCKS) {
    await sleep(600)
    const words = q
      .toLowerCase()
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .map((word) => word.replace(/s$/, ''))
    return mockState.media
      .filter((media) => !hikeId || media.hike_id === hikeId)
      .map((media) => {
        const hike = mockState.hikes.find((item) => item.id === media.hike_id)
        const sightings = mockState.sightings.filter((item) => item.media_id === media.id)
        const sighting = sightings.find((item) => {
          const chosen = item.verification.chosen
          const chosenName = `${chosen?.common_name ?? ''} ${chosen?.scientific_name ?? ''}`
            .toLowerCase()
          return words.some((word) => chosenName.includes(word))
        }) ?? sightings[0] ?? null
        return { media, hike_title: hike?.title ?? 'A hike', sighting, score: 0 }
      })
      .map((result) => ({
        ...result,
        score:
          words.reduce(
            (score, word) => score + (searchableText(result).includes(word) ? 1 : 0),
            0,
          ) / Math.max(1, words.length),
      }))
      .filter((result) => words.length === 0 || result.score > 0)
      .sort((first, second) => second.score - first.score)
  }
  const params = new URLSearchParams({ q })
  if (hikeId) params.set('hike_id', hikeId)
  return request<SearchResult[]>(`/search?${params.toString()}`)
}

export async function speciesNear(
  lat: number,
  lon: number,
  options: { month?: number; radiusKm?: number } = {},
): Promise<SpeciesNear[]> {
  if (USE_MOCKS) {
    await sleep(600)
    void lat
    void lon
    return mockState.hikes.at(-1)?.plan?.what_you_might_see ?? []
  }
  const params = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
    radius_km: String(options.radiusKm ?? 10),
  })
  if (options.month != null) params.set('month', String(options.month))
  return request<SpeciesNear[]>(`/species/near?${params.toString()}`)
}

export function mediaUrl(
  id: string,
  variant: MediaVariant = 'display',
): string {
  if (USE_MOCKS) {
    const uploadedUrl = mockState.objectUrls.get(id)
    if (uploadedUrl) return uploadedUrl
    const media = mockState.media.find((item) => item.id === id)
    const placeholder = media?.display_file_id ?? media?.thumb_file_id ?? 'misty'
    return `/mock/${placeholder}.svg`
  }
  return `${API_URL}/media/${encodeURIComponent(id)}/file?variant=${variant}`
}
