import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type ReactNode } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import {
  getHike,
  listHikes,
  mediaUrl,
  planHike,
  recap as createRecap,
  uploadMedia,
} from '../api/client'
import type {
  HikeCard,
  HikeDetail,
  MediaItem,
  Plan,
  Sighting,
} from '../api/types'
import { Masonry, RouteTrace, Waveform, type BoardEntry } from '../components/Board'
import MapView from '../components/MapView'
import { formatDate, formatDuration, formatLeaveBy, getSightingName } from '../components/format'
import {
  ErrorBox,
  MarkdownBlock,
  PageLoading,
  Panel,
  PlanSummary,
  StatusBadge,
  StepLoader,
} from '../components/Shared'

type Filter = 'all' | 'photos' | 'sightings' | 'sounds' | 'notes' | 'docs'

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'Everything' },
  { key: 'photos', label: 'Photos' },
  { key: 'sightings', label: 'Sightings' },
  { key: 'sounds', label: 'Sounds' },
  { key: 'notes', label: 'Notes' },
  { key: 'docs', label: 'Plan & route' },
]

/** Old `?tab=` links (NewHike, Search) still land somewhere sensible. */
function legacyOpen(tab: string | null): string | null {
  if (tab === 'plan') return 'plan'
  if (tab === 'recap') return 'recap'
  if (tab === 'overview') return 'route'
  return null
}

function plainText(markdown: string): string {
  return markdown.replace(/[#>*_`|[\]()-]/g, ' ').replace(/\s+/g, ' ').trim()
}

function HikeFolder() {
  const { id = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const [detail, setDetail] = useState<HikeDetail | null>(null)
  const [hikes, setHikes] = useState<HikeCard[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [uploadError, setUploadError] = useState('')
  const [planning, setPlanning] = useState(false)
  const [planError, setPlanError] = useState('')
  const [recapping, setRecapping] = useState(false)
  const [recapError, setRecapError] = useState('')
  const [kitState, setKitState] = useState<Record<string, boolean>>({})
  const [filter, setFilter] = useState<Filter>(params.get('tab') === 'sightings' ? 'sightings' : params.get('tab') === 'media' ? 'photos' : 'all')

  const open = params.get('open') ?? legacyOpen(params.get('tab'))

  const load = useCallback(async () => {
    try {
      const [loaded, hikeCards] = await Promise.all([getHike(id), listHikes()])
      setDetail(loaded)
      setHikes(hikeCards)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not open this hike.')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { void load() }, [load])

  const hike = detail?.hike
  const plan = hike?.plan

  const baseHike = useMemo(
    () => hikes.find((item) => item.id === hike?.based_on_hike_id) ?? null,
    [hike, hikes],
  )

  function openItem(key: string | null) {
    if (key) setParams({ open: key })
    else setParams({})
  }

  function retryLoad() {
    setLoading(true)
    setError('')
    void load()
  }

  async function onUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || !hike) return
    setUploading(true)
    setUploadProgress(0)
    setUploadError('')
    try {
      const result = await uploadMedia(hike.id, file, setUploadProgress)
      setDetail((current) => current ? {
        ...current,
        media: [result.media, ...current.media.filter((item) => item.id !== result.media.id)],
        sightings: result.sighting
          ? [result.sighting, ...current.sightings.filter((item) => item.id !== result.sighting?.id)]
          : current.sightings,
      } : current)
      openItem(`m-${result.media.id}`)
    } catch (uploadFailure) {
      setUploadError(uploadFailure instanceof Error ? uploadFailure.message : 'Could not upload this file.')
    } finally {
      setUploading(false)
    }
  }

  async function generatePlan() {
    if (!hike) return
    setPlanning(true)
    setPlanError('')
    try {
      const nextPlan = await planHike(hike.id)
      setDetail((current) => current ? { ...current, hike: { ...current.hike, plan: nextPlan } } : current)
    } catch (planFailure) {
      setPlanError(planFailure instanceof Error ? planFailure.message : 'Could not create the plan.')
    } finally {
      setPlanning(false)
    }
  }

  async function generateRecap() {
    if (!hike) return
    setRecapping(true)
    setRecapError('')
    try {
      const response = await createRecap(hike.id)
      setDetail((current) => current ? { ...current, hike: { ...current.hike, recap_md: response.recap_md } } : current)
    } catch (recapFailure) {
      setRecapError(recapFailure instanceof Error ? recapFailure.message : 'Could not write the recap.')
    } finally {
      setRecapping(false)
    }
  }

  if (loading) return <PageLoading />
  if (error || !detail) return <ErrorBox message={error || 'Hike not found.'} retry={retryLoad} />
  if (!hike) return <ErrorBox message="Hike details are missing." retry={retryLoad} />

  const sightingFor = (mediaId: string) => detail.sightings.find((item) => item.media_id === mediaId) ?? null
  const stats = hike.stats
  const facts = [
    formatDate(hike.date),
    stats?.distance_km != null ? `${stats.distance_km.toFixed(1)} km` : null,
    stats?.ascent_m != null ? `${Math.round(stats.ascent_m)} m climbed` : null,
    formatDuration(stats?.duration_s) ? `${formatDuration(stats?.duration_s)} h out` : null,
    detail.media.length ? `${detail.media.length} ${detail.media.length === 1 ? 'item' : 'items'}` : null,
  ].filter(Boolean) as string[]

  // ---- build the board -------------------------------------------------
  const docs: (BoardEntry & { filter: Filter[] })[] = []
  if (hike.route || stats) {
    docs.push({
      key: 'route', weight: 1.0, filter: ['docs'],
      node: <RouteTile detail={detail} onOpen={() => openItem('route')} />,
    })
  }
  if (hike.status === 'planned') {
    docs.push({
      key: 'plan', weight: plan ? 1.05 : 0.7, filter: ['docs'],
      node: <PlanTile plan={plan} planning={planning} onOpen={() => openItem('plan')} />,
    })
  }
  if (hike.status === 'completed') docs.push({
    key: 'recap', weight: hike.recap_md ? 0.9 : 0.5, filter: ['docs'],
    node: <RecapTile recap={hike.recap_md} onOpen={() => openItem('recap')} />,
  })

  const mediaEntries = [...detail.media]
    .sort((a, b) => (a.taken_at ?? a.created_at).localeCompare(b.taken_at ?? b.created_at))
    .map((item): BoardEntry & { filter: Filter[] } => {
      const sighting = sightingFor(item.id)
      const tags: Filter[] = []
      if (item.kind === 'photo' || item.kind === 'video') tags.push('photos')
      if (item.kind === 'audio') tags.push('sounds')
      if (item.kind === 'note') tags.push('notes')
      if (sighting && sighting.verification.status !== 'not_applicable') tags.push('sightings')
      const weight = item.kind === 'photo' ? 0.8 + ((item.id.charCodeAt(item.id.length - 1) % 3) * 0.18)
        : item.kind === 'audio' ? 0.5
          : item.kind === 'note' ? 0.45 + Math.min(0.5, (item.text?.length ?? 0) / 500)
            : 0.75
      return {
        key: item.id, weight, filter: tags,
        node: <MediaTile item={item} sighting={sighting} onOpen={() => openItem(`m-${item.id}`)} />,
      }
    })

  const uploadEntry: BoardEntry & { filter: Filter[] } = {
    key: 'upload', weight: 0.5, filter: ['photos', 'sounds', 'sightings'],
    node: (
      <label className={`tile tile-new tile-upload ${uploading ? 'busy' : ''}`}>
        {uploading ? (
          <>
            <span>Reading your file… {uploadProgress}%</span>
            <div className="upload-progress"><div style={{ width: `${uploadProgress}%` }} /></div>
            <span className="tile-new-hint">Gemini is captioning and identifying</span>
          </>
        ) : (
          <>
            <span className="tile-new-plus" aria-hidden="true">+</span>
            <span>Add a photo or sound</span>
            <span className="tile-new-hint">We'll caption it and check any species</span>
          </>
        )}
        <input accept="image/*,audio/*" hidden onChange={onUpload} type="file" disabled={uploading} />
      </label>
    ),
  }

  const all = [docs[0], uploadEntry, ...docs.slice(1), ...mediaEntries].filter(Boolean)
  const visible = all.filter((entry) => filter === 'all' || entry.filter.includes(filter))
  const countFor = (key: Filter) => key === 'all'
    ? docs.length + mediaEntries.length
    : [...docs, ...mediaEntries].filter((entry) => entry.filter.includes(key)).length

  // ---- sheet contents --------------------------------------------------
  let sheet: { title: string; kicker: string; body: ReactNode } | null = null
  if (open === 'route') {
    sheet = { title: hike.trail_name || 'Route', kicker: 'Route and stats', body: <RouteSheet detail={detail} /> }
  } else if (open === 'plan' && hike.status === 'planned') {
    sheet = {
      title: 'Plan for the day', kicker: formatDate(hike.date),
      body: (
        <PlanSection
          error={planError}
          kitState={kitState}
          onGenerate={() => void generatePlan()}
          onToggleKit={(item, checked) => setKitState((state) => ({ ...state, [item]: checked }))}
          plan={plan}
          planning={planning}
        />
      ),
    }
  } else if (open === 'recap') {
    sheet = {
      title: 'Recap', kicker: hike.title,
      body: <RecapSection error={recapError} onGenerate={() => void generateRecap()} recap={hike.recap_md} recapping={recapping} />,
    }
  } else if (open?.startsWith('m-')) {
    const item = detail.media.find((media) => media.id === open.slice(2))
    if (item) {
      const sighting = sightingFor(item.id)
      const name = sighting && sighting.verification.status !== 'not_applicable' ? getSightingName(sighting).common : null
      sheet = {
        title: name ?? (item.kind === 'note' ? 'Note' : item.kind === 'audio' ? 'Recording' : 'Photo'),
        kicker: item.taken_at ? new Date(item.taken_at).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : item.filename,
        body: <MediaSheet item={item} sighting={sighting} />,
      }
    }
  }

  return (
    <>
      <header className="folder-head">
        <Link to="/" className="back-link">All hikes</Link>
        <div className="folder-title-row">
          <h1>{hike.title}</h1>
          <StatusBadge status={hike.status} />
        </div>
        <p className="folder-sub">
          {hike.trail_name}{hike.hiker ? `, with ${hike.hiker}` : ''}
          {hike.based_on_hike_id && (
            <span className="based-on">Based on <Link to={`/hikes/${hike.based_on_hike_id}`}>{baseHike?.title ?? 'a previous hike'}</Link></span>
          )}
        </p>
        <ul className="folder-facts">{facts.map((fact) => <li key={fact}>{fact}</li>)}</ul>
      </header>

      <div className="board-bar">
        <div className="filter-chips" role="tablist" aria-label="Filter this hike">
          {FILTERS.map((item) => {
            const count = countFor(item.key)
            if (item.key !== 'all' && count === 0) return null
            return (
              <button
                key={item.key}
                type="button"
                role="tab"
                aria-selected={filter === item.key}
                className={`chip ${filter === item.key ? 'on' : ''}`}
                onClick={() => setFilter(item.key)}
              >
                {item.label}<span className="chip-count">{count}</span>
              </button>
            )
          })}
        </div>
      </div>

      {uploadError && <div style={{ marginBottom: 16 }}><ErrorBox message={uploadError} /></div>}
      <Masonry items={visible} />

      {sheet && (
        <Sheet title={sheet.title} kicker={sheet.kicker} onClose={() => openItem(null)}>
          {sheet.body}
        </Sheet>
      )}
    </>
  )
}

// ---- tiles ---------------------------------------------------------------

function RouteTile({ detail, onOpen }: { detail: HikeDetail; onOpen: () => void }) {
  const stats = detail.hike.stats
  return (
    <button type="button" className="tile tile-route" onClick={onOpen}>
      <RouteTrace route={detail.hike.route} />
      <div className="tile-foot">
        <strong>Route</strong>
        <span>
          {stats?.distance_km != null ? `${stats.distance_km.toFixed(1)} km` : 'No track'}
          {stats?.ascent_m != null ? `, ${Math.round(stats.ascent_m)} m up` : ''}
          {stats?.avg_hr != null ? `, ${Math.round(stats.avg_hr)} bpm avg` : ''}
        </span>
      </div>
    </button>
  )
}

function PlanTile({ plan, planning, onOpen }: { plan: Plan | null | undefined; planning: boolean; onOpen: () => void }) {
  if (!plan) {
    return (
      <button type="button" className="tile tile-doc" onClick={onOpen}>
        <span className="doc-kind">Plan</span>
        <p className="doc-lead">{planning ? 'Drafting your plan…' : 'No plan yet. Open to check the forecast, daylight and kit.'}</p>
      </button>
    )
  }
  const checks = plan.iterations.at(-1)?.checks ?? []
  const passed = checks.filter((check) => check.passed).length
  return (
    <button type="button" className="tile tile-doc tile-plan" onClick={onOpen}>
      <span className="doc-kind">Plan</span>
      <div className="plan-leave">
        <span>Leave by</span>
        <strong>{formatLeaveBy(plan.leave_by)}</strong>
      </div>
      <ul className="tile-checks" aria-label={`${passed} of ${checks.length} checks passed`}>
        {checks.map((check) => (
          <li key={check.name} className={check.passed ? 'ok' : 'bad'} title={check.detail}>{check.name}</li>
        ))}
      </ul>
      <p className="doc-meta">
        {passed} of {checks.length} checks pass
        {plan.revisions > 0 ? `. Argon revised it ${plan.revisions} ${plan.revisions === 1 ? 'time' : 'times'}` : ''}
      </p>
    </button>
  )
}

function RecapTile({ recap, onOpen }: { recap: string | null; onOpen: () => void }) {
  return (
    <button type="button" className="tile tile-doc tile-recap" onClick={onOpen}>
      <span className="doc-kind">Recap</span>
      {recap
        ? <p className="doc-body">{plainText(recap).slice(0, 220)}…</p>
        : <p className="doc-lead">Turn this folder into a short story of the day.</p>}
    </button>
  )
}

function SightingTag({ sighting }: { sighting: Sighting }) {
  const status = sighting.verification.status
  if (status === 'not_applicable') return null
  const name = getSightingName(sighting)
  return (
    <span className={`sighting-tag st-${status}`}>
      <span className="st-dot" aria-hidden="true" />
      {name.common}
      <span className="sr-only">, {status}</span>
    </span>
  )
}

function MediaTile({ item, sighting, onOpen }: { item: MediaItem; sighting: Sighting | null; onOpen: () => void }) {
  if (item.kind === 'note') {
    return (
      <button type="button" className="tile tile-note" onClick={onOpen}>
        <p>{item.text || item.caption}</p>
        <span className="tile-date">{formatDate(item.taken_at ?? item.created_at)}</span>
      </button>
    )
  }
  if (item.kind === 'audio') {
    return (
      <button type="button" className="tile tile-audio" onClick={onOpen}>
        <span className="audio-play" aria-hidden="true">▶</span>
        <Waveform seed={item.id} />
        <span className="audio-title">{item.caption || item.filename}</span>
        {sighting && <SightingTag sighting={sighting} />}
      </button>
    )
  }
  const isVideo = item.kind === 'video'
  const shape = item.id.charCodeAt(item.id.length - 1) % 3
  return (
    <button type="button" className={`tile tile-photo shape-${shape}`} onClick={onOpen} aria-label={item.caption || item.filename}>
      {isVideo
        ? <div className="video-poster"><span aria-hidden="true">▶</span>{item.filename}</div>
        : (
          <img
            src={mediaUrl(item.id, 'thumb')}
            alt=""
            loading="lazy"
            onError={(event) => { event.currentTarget.src = '/mock/misty.svg' }}
          />
        )}
      {sighting && <SightingTag sighting={sighting} />}
      {item.caption && <span className="photo-caption">{item.caption}</span>}
    </button>
  )
}

// ---- sheet ---------------------------------------------------------------

function Sheet({ title, kicker, onClose, children }: { title: string; kicker: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = previous
    }
  }, [onClose])
  return (
    <div className="sheet-layer" onClick={onClose}>
      <aside className="sheet" role="dialog" aria-modal="true" aria-label={title} onClick={(event) => event.stopPropagation()}>
        <div className="sheet-head">
          <div>
            <p className="sheet-kicker">{kicker}</p>
            <h2>{title}</h2>
          </div>
          <button type="button" className="sheet-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        <div className="sheet-body">{children}</div>
      </aside>
    </div>
  )
}

function RouteSheet({ detail }: { detail: HikeDetail }) {
  const { hike, sightings, media } = detail
  const stats = hike.stats
  const metrics: { label: string; value: string | null }[] = [
    { label: 'Distance', value: stats?.distance_km == null ? null : `${stats.distance_km.toFixed(1)} km` },
    { label: 'Duration', value: formatDuration(stats?.duration_s) },
    { label: 'Moving time', value: formatDuration(stats?.moving_s) },
    { label: 'Ascent', value: stats?.ascent_m == null ? null : `${Math.round(stats.ascent_m)} m` },
    { label: 'Descent', value: stats?.descent_m == null ? null : `${Math.round(stats.descent_m)} m` },
    { label: 'Average HR', value: stats?.avg_hr == null ? null : `${Math.round(stats.avg_hr)} bpm` },
    { label: 'Max HR', value: stats?.max_hr == null ? null : `${Math.round(stats.max_hr)} bpm` },
    { label: 'Moving speed', value: stats?.avg_moving_speed_kmh == null ? null : `${stats.avg_moving_speed_kmh.toFixed(1)} km/h` },
  ].filter((item) => item.value != null)
  const hasMapData = Boolean(hike.route || sightings.some((sighting) => sighting.location))
  const notes = media.filter((item) => item.kind === 'note' && item.text).map((item) => item.text!)
  return (
    <>
      {metrics.length > 0 ? (
        <dl className="stat-list">
          {metrics.map((metric) => (
            <div key={metric.label}><dt>{metric.label}</dt><dd>{metric.value}</dd></div>
          ))}
        </dl>
      ) : (
        <p className="muted">No track statistics yet. Add a GPX or FIT file to see distance, time and elevation.</p>
      )}
      {hasMapData
        ? <MapView route={hike.route} sightings={sightings} />
        : <div className="map-placeholder">Add a route to place this hike on the map.</div>}
      {notes.length > 0 && (
        <section className="section">
          <h3>Trail notes</h3>
          <ul className="why-list">{notes.map((note) => <li key={note}>{note}</li>)}</ul>
        </section>
      )}
    </>
  )
}

function MediaSheet({ item, sighting }: { item: MediaItem; sighting: Sighting | null }) {
  return (
    <>
      {item.kind === 'photo' && (
        <img className="sheet-photo" src={mediaUrl(item.id)} alt={item.caption ?? ''} onError={(event) => { event.currentTarget.src = '/mock/misty.svg' }} />
      )}
      {item.kind === 'video' && (
        <video className="sheet-photo" controls preload="metadata" src={mediaUrl(item.id, 'original')} />
      )}
      {item.kind === 'audio' && (
        <div className="sheet-audio">
          <Waveform seed={item.id} bars={60} />
          <audio controls preload="none" src={mediaUrl(item.id, 'original')} />
        </div>
      )}
      {item.kind === 'note'
        ? <p className="sheet-note">{item.text || item.caption}</p>
        : item.caption && <p className="sheet-caption">{item.caption}</p>}
      {item.tags.length > 0 && (
        <ul className="tag-list">{item.tags.map((tag) => <li key={tag}>{tag}</li>)}</ul>
      )}
      <p className="muted small">
        {item.location_source === 'exif' && 'Located from the photo. '}
        {item.location_source === 'track' && 'Placed on the track by its timestamp. '}
        {!item.location && item.kind !== 'note' && 'No location recorded. '}
      </p>
      {sighting && sighting.verification.status !== 'not_applicable' && (
        <section className="sheet-sighting">
          <h3 className="sheet-section-title">Identification</h3>
          <SightingDetails sighting={sighting} />
        </section>
      )}
    </>
  )
}

function SightingDetails({ sighting }: { sighting: Sighting }) {
  const identification = getSightingName(sighting)
  const verification = sighting.verification
  const candidate = verification.chosen ?? sighting.candidates[0]
  const specialist = verification.specialist
  let specialistLine = 'No second opinion'
  if (specialist && verification.specialist_agrees === 'species') {
    const service = specialist.source === 'plantnet' ? 'Pl@ntNet' : 'mushroom.id'
    specialistLine = `${service} agrees · ${Math.round(specialist.top_score * 100)}%`
  } else if (specialist && verification.specialist_agrees === 'genus') {
    const service = specialist.source === 'plantnet' ? 'Pl@ntNet' : 'mushroom.id'
    const genus = specialist.top_name.split(' ')[0]
    specialistLine = `${service} agrees on genus (${genus}) · ${Math.round(specialist.top_score * 100)}%`
  } else if (specialist && verification.specialist_agrees === 'no') {
    const service = specialist.source === 'plantnet' ? 'Pl@ntNet' : 'mushroom.id'
    const name = specialist.top_common_name ? `${specialist.top_common_name} (${specialist.top_name})` : specialist.top_name
    specialistLine = `${service} suggests ${name} instead · ${Math.round(specialist.top_score * 100)}%`
  }
  const others = sighting.candidates.filter((item) => item.scientific_name !== candidate?.scientific_name)
  return (
    <>
      <div className="sighting-title-line">
        <div><h3>{identification.common}</h3>{identification.scientific && <div className="science">{identification.scientific}</div>}</div>
        <StatusBadge status={verification.status} />
      </div>
      {candidate && <p className="confidence-line">Confidence · <strong>{Math.round(candidate.confidence * 100)}%</strong></p>}
      <p className="specialist-line">{specialistLine}</p>
      {verification.gbif_nearby_count != null && (
        <p className="gbif-line">{verification.gbif_nearby_count} GBIF records within 10 km this season</p>
      )}
      <div className="small" style={{ marginTop: 12, fontWeight: 700 }}>Why</div>
      {verification.reasons.length > 0
        ? <ul className="why-list">{verification.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
        : <p className="why-list">No explanation was provided for this suggestion.</p>}
      {others.length > 0 && (
        <p className="candidate-list">Other suggestions: {others.map((item) => `${item.common_name} (${Math.round(item.confidence * 100)}%)`).join(' · ')}</p>
      )}
      {sighting.safety_note && <div className="warning-box">{sighting.safety_note}</div>}
    </>
  )
}

function PlanSection({
  plan,
  planning,
  error,
  onGenerate,
  kitState,
  onToggleKit,
}: {
  plan: Plan | null | undefined
  planning: boolean
  error: string
  onGenerate: () => void
  kitState: Record<string, boolean>
  onToggleKit: (item: string, checked: boolean) => void
}) {
  if (planning) return <StepLoader label="Putting your plan together" />
  if (!plan) {
    return (
      <Panel className="panel-pad">
        <h2>Start with a thoughtful plan.</h2>
        <p className="muted">The report combines daylight, route pace, forecast checks and sourced hazards.</p>
        {error && <div style={{ margin: '16px 0' }}><ErrorBox message={error} retry={onGenerate} /></div>}
        <button className="button" onClick={onGenerate}>Generate plan <span aria-hidden="true">→</span></button>
      </Panel>
    )
  }
  const checks = plan.iterations.at(-1)?.checks ?? []
  const firstFailures = plan.iterations[0]?.checks.filter((check) => !check.passed) ?? []
  return (
    <>
      <div className="plan-disclaimer"><strong>Suggested plan — check conditions before you go.</strong> Forecasts and route estimates can change; use your own judgement on the day.</div>
      <div className="leave-banner">
        <span aria-hidden="true">◷</span>
        <div><div className="small">Leave by</div><div className="leave-time">{formatLeaveBy(plan.leave_by)}</div></div>
        <span className="muted small">Europe/London local time</span>
      </div>
      {plan.forecast_summary && <p className="forecast">{plan.forecast_summary}</p>}
      <Panel className="panel-pad section">
        <PlanSummary plan={plan} />
      </Panel>
      <div className="section">
        <div className="section-header"><h2>Verification checks</h2><span className="small muted">Final draft</span></div>
        <Panel className="panel-pad">
          <div className="check-list">
            {checks.map((check) => (
              <div className={`check-item ${check.passed ? '' : 'failed'}`} key={check.name}>
                <span className="check-icon">{check.passed ? '✓' : '✕'}</span>
                <div><strong className="small">{check.name}</strong><div className="check-detail">{check.detail}</div></div>
              </div>
            ))}
          </div>
          <p className="muted small" style={{ margin: '16px 0 0' }}>Argon revised the plan {plan.revisions} {plan.revisions === 1 ? 'time' : 'times'}.</p>
          {firstFailures.length > 0 && (
            <details className="old-draft">
              <summary>See what the first draft missed</summary>
              <ul className="why-list">{firstFailures.map((check) => <li key={check.name}><strong>{check.name}:</strong> {check.detail}</li>)}</ul>
            </details>
          )}
        </Panel>
      </div>
      <div className="section">
        <h2>Pack for the day</h2>
        <Panel className="panel-pad">
          {plan.final.kit.map((item) => (
            <label className="kit-row" key={item.item}>
              <input
                checked={kitState[item.item] ?? item.done}
                onChange={(event) => onToggleKit(item.item, event.target.checked)}
                type="checkbox"
              />
              <span><strong className="small">{item.item}</strong><p className="kit-reason">{item.reason}</p></span>
            </label>
          ))}
        </Panel>
      </div>
      <div className="section">
        <h2>Hazards and sources</h2>
        <Panel className="panel-pad">
          {plan.final.hazards.map((hazard, index) => (
            <div className="hazard-item" key={`${hazard.text}-${index}`}>
              {hazard.text}
              {hazard.source_url
                ? <a href={hazard.source_url} target="_blank" rel="noopener noreferrer">{hazard.source_title || 'Read source'} ↗</a>
                : <span className="warning-box" style={{ display: 'block' }}>No source — treat with caution</span>}
            </div>
          ))}
        </Panel>
      </div>
      {plan.what_you_might_see.length > 0 && (
        <div className="section">
          <h2>What you might see</h2>
          <div className="species-list">
            {plan.what_you_might_see.map((species) => (
              <div className="species-chip" key={species.scientific_name}>
                <span>{species.count} records</span><strong>{species.name}</strong><em>{species.scientific_name}</em>
              </div>
            ))}
          </div>
        </div>
      )}
      {plan.final.notes.length > 0 && (
        <div className="section">
          <h2>Keep in mind</h2>
          <Panel className="panel-pad"><ul className="why-list">{plan.final.notes.map((note) => <li key={note}>{note}</li>)}</ul></Panel>
        </div>
      )}
    </>
  )
}

function RecapSection({
  recap,
  recapping,
  error,
  onGenerate,
}: {
  recap: string | null
  recapping: boolean
  error: string
  onGenerate: () => void
}) {
  if (recapping) return <StepLoader label="Gathering the hike folder" />
  if (recap) {
    return (
      <Panel className="panel-pad">
        <span className="eyebrow">A look back</span>
        <MarkdownBlock content={recap} />
        <button className="button-quiet" onClick={onGenerate}>Write a fresh recap</button>
      </Panel>
    )
  }
  return (
    <Panel className="panel-pad">
      <h2>A little reflection, gathered together.</h2>
      <p className="muted">Create a short recap from this hike’s stats, media and notes.</p>
      {error && <div style={{ margin: '16px 0' }}><ErrorBox message={error} retry={onGenerate} /></div>}
      <button className="button" onClick={onGenerate}>Generate recap</button>
    </Panel>
  )
}

export default HikeFolder
