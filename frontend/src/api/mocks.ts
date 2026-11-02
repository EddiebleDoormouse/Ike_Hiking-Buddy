import type {
  Candidate,
  Check,
  Hike,
  HikeCreate,
  HikeDetail,
  HikeStats,
  MediaItem,
  Plan,
  PlanDraft,
  Sighting,
} from './types'

const createdAt = '2026-10-24T08:30:00.000Z'

function loopRoute(
  lat: number,
  lon: number,
  radiusLat: number,
  radiusLon: number,
  count = 40,
): [number, number][] {
  return Array.from({ length: count }, (_, index) => {
    const angle = (2 * Math.PI * index) / (count - 1)
    const irregularity = 1 + 0.12 * Math.sin(angle * 3) + 0.05 * Math.cos(angle * 5)
    return [
      lon + Math.cos(angle) * radiusLon * irregularity,
      lat + Math.sin(angle) * radiusLat * irregularity,
    ]
  })
}

const planDraft: PlanDraft = {
  summary_md:
    '## A steady day on the Kinder plateau\n\nStart from Edale and take the gradual ascent via **Grindslow Knoll**. Keep to the marked paths and leave time to turn back if cloud closes in.\n\n- Follow the Pennine Way north\n- Pause at Kinder Downfall only if conditions are calm\n- Return by the same route before dusk',
  start_time_local: '08:30',
  est_duration_min: 390,
  kit: [
    { item: 'Waterproof jacket and trousers', reason: 'Showers and strong gusts are possible on the plateau.', done: true },
    { item: 'Warm mid-layer', reason: 'Wind chill can make the exposed ridge feel much colder.', done: true },
    { item: 'Map and compass', reason: 'Low cloud can reduce visibility quickly.', done: false },
    { item: 'Head torch', reason: 'Keep a light in reserve if the return takes longer.', done: false },
    { item: 'Water and snacks', reason: 'Allow for a long day with limited facilities on route.', done: true },
    { item: 'Grippy walking boots', reason: 'Boggy ground and uneven gritstone are likely.', done: false },
    { item: 'Gloves and hat', reason: 'Useful on the windy upper slopes.', done: false },
  ],
  hazards: [
    {
      text: 'Exposed plateau sections can become difficult to navigate in low cloud.',
      source_url: 'https://www.peakdistrict.gov.uk/visiting/planning-your-visit/safety',
      source_title: 'Peak District National Park — safety',
    },
    {
      text: 'Kinder Downfall may have strong gusts and slippery ground near the edge.',
      source_url: 'https://www.nationaltrust.org.uk/visit/peak-district/kinder-edale',
      source_title: 'National Trust — Kinder and Edale',
    },
    {
      text: 'Check the latest mountain forecast before setting out.',
      source_url: 'https://www.metoffice.gov.uk/weather/specialist-forecasts/mountain',
      source_title: 'Met Office mountain forecast',
    },
  ],
  notes: [
    'Forecasts are uncertain; check conditions again on the morning.',
    'Turn around early if visibility or wind deteriorates.',
    'Estimated timings are a guide, not a promise.',
  ],
}

const firstDraft: PlanDraft = {
  ...planDraft,
  summary_md:
    'A direct loop over the Kinder plateau with an early start. The first draft kept the edge path in the afternoon.',
  start_time_local: '09:00',
  hazards: [{ text: 'Check weather before leaving.', source_url: null, source_title: null }],
}

const firstChecks: Check[] = [
  { name: 'Finish ≥ 60 min before sunset', passed: false, detail: 'The first estimate reached the car park too close to sunset.' },
  { name: 'Maximum gust < 50 km/h', passed: true, detail: 'Forecast peak gust is 46 km/h.' },
  { name: 'Precipitation probability < 70%', passed: true, detail: 'Peak hourly probability is 45%.' },
  { name: 'Cold-weather kit included', passed: true, detail: 'A warm layer is on the checklist.' },
  { name: 'Every hazard has a source', passed: false, detail: 'The first draft did not cite its hazard claim.' },
  { name: 'Duration fits daylight and Naismith estimate', passed: true, detail: 'The route estimate is within the available daylight.' },
  { name: 'Start after sunrise', passed: true, detail: '09:00 is after sunrise.' },
]

const finalChecks: Check[] = [
  { name: 'Finish ≥ 60 min before sunset', passed: true, detail: 'The 08:30 start leaves a comfortable daylight buffer.' },
  { name: 'Maximum gust < 50 km/h', passed: false, detail: 'Gusts up to 56 km/h on the plateau at 14:00 — plan keeps you off the edge path after 13:00.' },
  { name: 'Precipitation probability < 70%', passed: true, detail: 'Peak hourly probability is 45%.' },
  { name: 'Cold-weather kit included', passed: true, detail: 'Warm layer, gloves and hat are on the checklist.' },
  { name: 'Every hazard has a source', passed: true, detail: 'All three hazards link to a named source.' },
  { name: 'Duration fits daylight and Naismith estimate', passed: true, detail: '390 minutes is within the daylight window.' },
  { name: 'Start after sunrise', passed: true, detail: '08:30 is after sunrise.' },
]

const fullPlan: Plan = {
  final: planDraft,
  iterations: [
    { draft: firstDraft, checks: firstChecks },
    { draft: planDraft, checks: finalChecks },
  ],
  revisions: 1,
  what_you_might_see: [
    { name: 'Red grouse', scientific_name: 'Lagopus lagopus scotica', count: 4 },
    { name: 'Mountain hare', scientific_name: 'Lepus timidus', count: 2 },
    { name: 'Bilberry', scientific_name: 'Vaccinium myrtillus', count: 18 },
    { name: 'Meadow pipit', scientific_name: 'Anthus pratensis', count: 7 },
  ],
  leave_by: '2026-10-31T08:30:00+00:00',
  forecast_summary: 'Cool and breezy with scattered showers; gusts may reach 56 km/h on exposed ground.',
}

const ivstats: HikeStats = {
  distance_km: 12.4,
  duration_s: 16440,
  moving_s: 14340,
  ascent_m: 428,
  descent_m: 431,
  avg_hr: 132,
  max_hr: 174,
  start_time: '2026-10-10T07:42:00+01:00',
  end_time: '2026-10-10T12:16:00+01:00',
  avg_moving_speed_kmh: 3.11,
}

const kinderStats: HikeStats = {
  distance_km: 16.8,
  duration_s: 24540,
  moving_s: 20220,
  ascent_m: 781,
  descent_m: 779,
  avg_hr: null,
  max_hr: null,
  start_time: '2026-09-19T08:10:00+01:00',
  end_time: '2026-09-19T14:59:00+01:00',
  avg_moving_speed_kmh: 2.99,
}

export const mockHikes: Hike[] = [
  {
    id: 'hike-ivinghoe',
    title: 'Ivinghoe Beacon loop',
    trail_name: 'Ivinghoe Beacon, Chilterns',
    hiker: 'Edouard',
    date: '2026-10-10',
    status: 'completed',
    route: { type: 'LineString', coordinates: loopRoute(51.84, -0.61, 0.012, 0.02) },
    start: { type: 'Point', coordinates: [-0.61, 51.84] },
    stats: ivstats,
    pace_factor: 1,
    plan: null,
    recap_md: null,
    created_at: createdAt,
  },
  {
    id: 'hike-kinder',
    title: 'Kinder Scout circuit',
    trail_name: 'Kinder Scout, Peak District',
    hiker: 'Edouard',
    date: '2026-09-19',
    status: 'completed',
    route: { type: 'LineString', coordinates: loopRoute(53.38, -1.87, 0.022, 0.035) },
    start: { type: 'Point', coordinates: [-1.87, 53.38] },
    stats: kinderStats,
    pace_factor: 1,
    plan: null,
    recap_md: null,
    created_at: createdAt,
  },
  {
    id: 'hike-kinder-planned',
    title: "Kinder Scout with [friend]'s pace",
    trail_name: 'Kinder Scout, Peak District',
    hiker: 'Edouard',
    date: '2026-10-31',
    status: 'planned',
    based_on_hike_id: 'hike-kinder',
    route: null,
    start: { type: 'Point', coordinates: [-1.87, 53.38] },
    stats: null,
    pace_factor: 1.15,
    plan: fullPlan,
    recap_md: null,
    created_at: createdAt,
  },
]

const buzzard: Candidate = {
  common_name: 'Common Buzzard',
  scientific_name: 'Buteo buteo',
  confidence: 0.42,
  group: 'bird',
}
const flyAgaric: Candidate = {
  common_name: 'Fly agaric',
  scientific_name: 'Amanita muscaria',
  confidence: 0.82,
  group: 'fungus',
}
const blusher: Candidate = {
  common_name: 'Blusher',
  scientific_name: 'Amanita rubescens',
  confidence: 0.1,
  group: 'fungus',
}
const pantherCap: Candidate = {
  common_name: 'Panther cap',
  scientific_name: 'Amanita pantherina',
  confidence: 0.05,
  group: 'fungus',
}
const fox: Candidate = {
  common_name: 'Red fox',
  scientific_name: 'Vulpes vulpes',
  confidence: 0.86,
  group: 'mammal',
}
const domesticDog: Candidate = {
  common_name: 'Domestic dog',
  scientific_name: 'Canis familiaris',
  confidence: 0.07,
  group: 'mammal',
}
const badger: Candidate = {
  common_name: 'Badger',
  scientific_name: 'Meles meles',
  confidence: 0.03,
  group: 'mammal',
}
const redKite: Candidate = {
  common_name: 'Red kite',
  scientific_name: 'Milvus milvus',
  confidence: 0.31,
  group: 'bird',
}
const kestrel: Candidate = {
  common_name: 'Kestrel',
  scientific_name: 'Falco tinnunculus',
  confidence: 0.12,
  group: 'bird',
}
const heather: Candidate = {
  common_name: 'Heather / Ling',
  scientific_name: 'Calluna vulgaris',
  confidence: 0.78,
  group: 'plant',
}
const bellHeather: Candidate = {
  common_name: 'Bell heather',
  scientific_name: 'Erica cinerea',
  confidence: 0.15,
  group: 'plant',
}

function makeSighting(
  id: string,
  hikeId: string,
  mediaId: string,
  candidates: Candidate[],
  chosen: Candidate | null,
  status: Sighting['verification']['status'],
  details: Partial<Sighting['verification']>,
  location: Sighting['location'],
  safetyNote: string | null = null,
): Sighting {
  return {
    id,
    hike_id: hikeId,
    media_id: mediaId,
    candidates,
    verification: {
      status,
      chosen,
      gbif_nearby_count: chosen ? 23 : null,
      gbif_key: chosen ? 2434116 : null,
      specialist: null,
      specialist_agrees: null,
      reasons: [],
      ...details,
    },
    location,
    seen_at: '2026-10-10T08:12:00+01:00',
    safety_note: safetyNote,
  }
}

export const mockMedia: MediaItem[] = [
  {
    id: 'media-fox',
    hike_id: 'hike-ivinghoe',
    kind: 'photo',
    filename: 'ridge-at-dawn.jpg',
    mime: 'image/jpeg',
    original_file_id: 'fox',
    display_file_id: 'fox',
    thumb_file_id: 'fox',
    taken_at: '2026-10-10T07:58:00+01:00',
    location: { type: 'Point', coordinates: [-0.616, 51.841] },
    location_source: 'exif',
    caption: 'Red fox crossing the misty ridge at dawn',
    tags: ['fox', 'dawn', 'ridge', 'wildlife'],
    text: null,
    created_at: createdAt,
  },
  {
    id: 'media-mushroom',
    hike_id: 'hike-ivinghoe',
    kind: 'photo',
    filename: 'fly-agaric.jpg',
    mime: 'image/jpeg',
    original_file_id: 'mushroom',
    display_file_id: 'mushroom',
    thumb_file_id: 'mushroom',
    taken_at: '2026-10-10T09:14:00+01:00',
    location: { type: 'Point', coordinates: [-0.604, 51.844] },
    location_source: 'track',
    caption: 'Fly agaric (red mushroom) in birch woodland',
    tags: ['red mushroom', 'fungus', 'birch', 'woodland'],
    text: null,
    created_at: createdAt,
  },
  {
    id: 'media-misty',
    hike_id: 'hike-ivinghoe',
    kind: 'photo',
    filename: 'misty-views.jpg',
    mime: 'image/jpeg',
    original_file_id: 'misty',
    display_file_id: 'misty',
    thumb_file_id: 'misty',
    taken_at: null,
    location: null,
    location_source: null,
    caption: 'Misty views over Edale',
    tags: ['misty views', 'landscape', 'valley'],
    text: null,
    created_at: createdAt,
  },
  {
    id: 'media-heather',
    hike_id: 'hike-kinder',
    kind: 'photo',
    filename: 'heather.jpg',
    mime: 'image/jpeg',
    original_file_id: 'heather',
    display_file_id: 'heather',
    thumb_file_id: 'heather',
    taken_at: '2026-09-19T11:30:00+01:00',
    location: { type: 'Point', coordinates: [-1.889, 53.383] },
    location_source: 'track',
    caption: 'Heather and ling beside a distant buzzard-like silhouette',
    tags: ['heather', 'ling', 'Calluna vulgaris', 'buzzard', 'bird', 'moorland'],
    text: null,
    created_at: createdAt,
  },
  {
    id: 'media-trig',
    hike_id: 'hike-kinder',
    kind: 'photo',
    filename: 'summit-trig.jpg',
    mime: 'image/jpeg',
    original_file_id: 'trig',
    display_file_id: 'trig',
    thumb_file_id: 'trig',
    taken_at: '2026-09-19T12:06:00+01:00',
    location: { type: 'Point', coordinates: [-1.87, 53.38] },
    location_source: 'exif',
    caption: 'Trig point above the Peak District moorland',
    tags: ['summit', 'trig point', 'moorland'],
    text: null,
    created_at: createdAt,
  },
  {
    id: 'media-audio',
    hike_id: 'hike-kinder',
    kind: 'audio',
    filename: 'morning-birdsong.mp3',
    mime: 'audio/mpeg',
    original_file_id: 'birdsong-original',
    display_file_id: null,
    thumb_file_id: null,
    taken_at: '2026-09-19T08:40:00+01:00',
    location: null,
    location_source: null,
    caption: 'Birdsong on the morning walk',
    tags: ['birds', 'audio', 'morning'],
    text: null,
    created_at: createdAt,
  },
]

export const mockSightings: Sighting[] = [
  makeSighting(
    'sighting-fox',
    'hike-ivinghoe',
    'media-fox',
    [fox, domesticDog, badger],
    fox,
    'confirmed',
    {
      gbif_nearby_count: 18,
      gbif_key: 5219173,
      specialist: null,
      specialist_agrees: null,
      reasons: ['The leading candidate is Red fox (Vulpes vulpes) at 86%.', 'GBIF has 18 nearby seasonal records.', 'The image and location support a fox identification, though they are not proof.'],
    },
    { type: 'Point', coordinates: [-0.616, 51.841] },
  ),
  makeSighting(
    'sighting-heather',
    'hike-kinder',
    'media-heather',
    [heather, bellHeather],
    heather,
    'confirmed',
    {
      gbif_nearby_count: 42,
      gbif_key: 2689683,
      specialist: {
        source: 'plantnet',
        top_name: 'Calluna vulgaris',
        top_common_name: 'Heather / Ling',
        top_score: 0.71,
        alternatives: [{ name: 'Erica cinerea', common_name: 'Bell heather', score: 0.18 }],
        gbif_key: 2689683,
      },
      specialist_agrees: 'species',
      reasons: ['The leading candidate is Heather / Ling (Calluna vulgaris) at 78%.', 'Pl@ntNet independently identifies Calluna vulgaris at 71%.', 'GBIF has 42 nearby seasonal records; these provide context, not proof.'],
    },
    { type: 'Point', coordinates: [-1.889, 53.383] },
  ),
  makeSighting(
    'sighting-mushroom',
    'hike-ivinghoe',
    'media-mushroom',
    [flyAgaric, blusher, pantherCap],
    flyAgaric,
    'plausible',
    {
      gbif_nearby_count: 3,
      gbif_key: 5401234,
      specialist: {
        source: 'mushroom_id',
        top_name: 'Amanita rubescens',
        top_common_name: 'Blusher',
        top_score: 0.64,
        alternatives: [{ name: 'Amanita muscaria', common_name: 'Fly agaric', score: 0.25 }],
        gbif_key: 5401234,
      },
      specialist_agrees: 'no',
      reasons: ['The image model suggests Fly agaric, but confidence is not definitive.', 'A second opinion suggests a different Amanita species.', 'Nearby seasonal records provide context, not proof.'],
    },
    { type: 'Point', coordinates: [-0.604, 51.844] },
    'Many Amanita species are deadly. Never eat a wild mushroom based on an app.',
  ),
  makeSighting(
    'sighting-buzzard',
    'hike-kinder',
    'media-heather',
    [buzzard, redKite, kestrel],
    buzzard,
    'unsure',
    {
      gbif_nearby_count: 0,
      gbif_key: 2480583,
      specialist: null,
      specialist_agrees: null,
      reasons: ['The image is partly obscured and candidate confidence is 42%.', 'No nearby seasonal records were found.', 'Treat this as an uncertain suggestion.'],
    },
    { type: 'Point', coordinates: [-1.889, 53.383] },
  ),
  makeSighting(
    'sighting-landscape',
    'hike-ivinghoe',
    'media-misty',
    [],
    null,
    'not_applicable',
    {
      chosen: null,
      gbif_nearby_count: null,
      gbif_key: null,
      specialist: null,
      specialist_agrees: null,
      reasons: ['This is a landscape photograph, not an organism identification.'],
    },
    null,
  ),
]

export const mockState = {
  hikes: mockHikes,
  media: mockMedia,
  sightings: mockSightings,
  objectUrls: new Map<string, string>(),
}

export function asHikeDetail(hike: Hike): HikeDetail {
  return {
    hike,
    media: mockState.media.filter((item) => item.hike_id === hike.id),
    sightings: mockState.sightings.filter((sighting) => sighting.hike_id === hike.id),
  }
}

export function createMockHike(body: HikeCreate): Hike {
  const hike: Hike = {
    ...body,
    id: `hike-${Date.now()}`,
    route: null,
    start: null,
    stats: null,
    pace_factor: 1,
    plan: null,
    recap_md: null,
    created_at: new Date().toISOString(),
  }
  mockState.hikes.unshift(hike)
  return hike
}
