import { useCallback, useEffect, useMemo, useState, type ChangeEvent } from 'react'
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
  UploadMediaResponse,
} from '../api/types'
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

type TabName = 'overview' | 'media' | 'sightings' | 'plan' | 'recap'

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
  const [uploadResult, setUploadResult] = useState<UploadMediaResponse | null>(null)
  const [planning, setPlanning] = useState(false)
  const [planError, setPlanError] = useState('')
  const [recapping, setRecapping] = useState(false)
  const [recapError, setRecapError] = useState('')
  const [kitState, setKitState] = useState<Record<string, boolean>>({})

  const tab = (params.get('tab') as TabName | null) ?? 'overview'
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

  function changeTab(nextTab: TabName) {
    if (nextTab === 'overview') setParams({})
    else setParams({ tab: nextTab })
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
      setUploadResult(result)
      setDetail((current) => current ? {
        ...current,
        media: [result.media, ...current.media.filter((item) => item.id !== result.media.id)],
        sightings: result.sighting
          ? [result.sighting, ...current.sightings.filter((item) => item.id !== result.sighting?.id)]
          : current.sightings,
      } : current)
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

  const tabs: { key: TabName; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'media', label: 'Media' },
    { key: 'sightings', label: 'Sightings' },
    ...(hike.status === 'planned' ? [{ key: 'plan' as const, label: 'Plan' }] : []),
    { key: 'recap', label: 'Recap' },
  ]
  const isValidTab = tabs.some((item) => item.key === tab)
  const activeTab = isValidTab ? tab : 'overview'

  return (
    <>
      <div className="page-heading detail-heading">
        <div>
          <span className="eyebrow">{hike.trail_name}</span>
          <h1 className="detail-title">{hike.title}</h1>
          <p className="subheading">{hike.hiker} <span aria-hidden="true">·</span> {formatDate(hike.date)}</p>
          {hike.based_on_hike_id && (
            <p className="detail-links">
              Based on <Link to={`/hikes/${hike.based_on_hike_id}`}>{baseHike?.title ?? 'a previous hike'}</Link>
            </p>
          )}
        </div>
        <StatusBadge status={hike.status} />
      </div>
      <nav className="tab-row" aria-label="Hike sections">
        {tabs.map((item) => (
          <button
            aria-current={activeTab === item.key ? 'page' : undefined}
            className={`tab ${activeTab === item.key ? 'active' : ''}`}
            key={item.key}
            onClick={() => changeTab(item.key)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </nav>
      {activeTab === 'overview' && <Overview detail={detail} />}
      {activeTab === 'media' && (
        <MediaSection
          detail={detail}
          onUpload={onUpload}
          uploadError={uploadError}
          uploadProgress={uploadProgress}
          uploadResult={uploadResult}
          uploading={uploading}
        />
      )}
      {activeTab === 'sightings' && <SightingsSection detail={detail} />}
      {activeTab === 'plan' && hike.status === 'planned' && (
        <PlanSection
          error={planError}
          kitState={kitState}
          onGenerate={() => void generatePlan()}
          onToggleKit={(item, checked) => setKitState((state) => ({ ...state, [item]: checked }))}
          plan={plan}
          planning={planning}
        />
      )}
      {activeTab === 'recap' && (
        <RecapSection
          error={recapError}
          onGenerate={() => void generateRecap()}
          recap={hike.recap_md}
          recapping={recapping}
        />
      )}
    </>
  )
}

function Overview({ detail }: { detail: HikeDetail }) {
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
  const notes = hike.plan?.final.notes ?? media
    .filter((item) => item.kind === 'note' && item.text)
    .map((item) => item.text!)

  return (
    <>
      {metrics.length > 0 ? (
        <Panel className="stats-grid">
          {metrics.map((metric) => (
            <div className="stat-item" key={metric.label}>
              <div className="stat-value">{metric.value}</div>
              <div className="stat-label">{metric.label}</div>
            </div>
          ))}
        </Panel>
      ) : (
        <div className="map-placeholder">No track statistics yet. Add a GPX or FIT track to see distance, time and elevation.</div>
      )}
      <section className="section">
        <div className="section-header"><h2>Route and sightings</h2></div>
        {hasMapData
          ? <MapView route={hike.route} sightings={sightings} />
          : <div className="map-placeholder"><div><strong>No track yet</strong><br />Add a route to place this hike on the map.</div></div>}
      </section>
      {notes.length > 0 && (
        <section className="section">
          <h2>Trail notes</h2>
          <Panel className="panel-pad">
            <ul className="why-list">{notes.map((note) => <li key={note}>{note}</li>)}</ul>
          </Panel>
        </section>
      )}
    </>
  )
}

function MediaSection({
  detail,
  onUpload,
  uploading,
  uploadProgress,
  uploadError,
  uploadResult,
}: {
  detail: HikeDetail
  onUpload: (event: ChangeEvent<HTMLInputElement>) => void
  uploading: boolean
  uploadProgress: number
  uploadError: string
  uploadResult: UploadMediaResponse | null
}) {
  const photos = detail.media.filter((item) => item.kind === 'photo')
  const audio = detail.media.filter((item) => item.kind === 'audio')
  const notes = detail.media.filter((item) => item.kind === 'note')
  return (
    <>
      <div className="section-header">
        <div><h2>Memories from the trail</h2><p className="muted small">Photos, recordings and notes, together.</p></div>
        <label className="button button-small">
          {uploading ? 'Uploading…' : '＋ Add media'}
          <input
            accept="image/*,audio/*"
            capture="environment"
            hidden
            onChange={onUpload}
            type="file"
            disabled={uploading}
          />
        </label>
      </div>
      {uploading && (
        <Panel className="panel-pad" style={{ marginBottom: 16 }}>
          <strong className="small">Uploading your file… {uploadProgress}%</strong>
          <div className="upload-progress"><div style={{ width: `${uploadProgress}%` }} /></div>
        </Panel>
      )}
      {uploadError && <div style={{ marginBottom: 16 }}><ErrorBox message={uploadError} /></div>}
      {uploadResult && <UploadResult result={uploadResult} />}
      {photos.length > 0 && (
        <div className="media-grid">
          {photos.map((item) => <PhotoCard item={item} key={item.id} />)}
        </div>
      )}
      {audio.length > 0 && (
        <section className="section">
          <h2>Audio</h2>
          <div className="media-grid">
            {audio.map((item) => (
              <Panel className="audio-card" key={item.id}>
                <h3>{item.caption || item.filename}</h3>
                <audio controls preload="none" src={item.display_file_id ? mediaUrl(item.id) : undefined} />
                {!item.display_file_id && <p className="muted small">Audio preview isn’t available in this demo.</p>}
                <p className="muted small">{formatDate(item.taken_at ?? item.created_at)}</p>
              </Panel>
            ))}
          </div>
        </section>
      )}
      {notes.length > 0 && (
        <section className="section">
          <h2>Notes</h2>
          <div className="media-grid">
            {notes.map((item) => <Panel className="note-card" key={item.id}>{item.text || item.caption}</Panel>)}
          </div>
        </section>
      )}
      {photos.length === 0 && audio.length === 0 && notes.length === 0 && (
        <div className="empty-state"><h2>No media yet</h2><p className="muted">Add a photo or recording from the trail.</p></div>
      )}
    </>
  )
}

function PhotoCard({ item }: { item: MediaItem }) {
  return (
    <article className="media-card">
      <img className="media-image" src={mediaUrl(item.id, 'thumb')} alt="" onError={(event) => { event.currentTarget.src = '/mock/misty.svg' }} />
      <div className="media-caption">
        {item.caption || item.filename}
        <p>{item.taken_at ? formatDate(item.taken_at) : 'Date and location not recorded'}</p>
      </div>
    </article>
  )
}

function UploadResult({ result }: { result: UploadMediaResponse }) {
  const media = result.media
  const sighting = result.sighting
  return (
    <Panel className="panel-pad" style={{ marginBottom: 18 }}>
      <span className="eyebrow">Just added</span>
      <div className="media-grid" style={{ gridTemplateColumns: 'minmax(0, 1fr) 1.3fr', alignItems: 'start' }}>
        {media.kind === 'photo'
          ? <img className="media-image" style={{ borderRadius: 14 }} src={mediaUrl(media.id)} alt="" />
          : <div className="map-placeholder">Audio note added</div>}
        <div>
          <p><strong>{media.caption || media.filename}</strong></p>
          {sighting && <SightingDetails sighting={sighting} />}
        </div>
      </div>
    </Panel>
  )
}

function SightingsSection({ detail }: { detail: HikeDetail }) {
  if (!detail.sightings.length) {
    return <div className="empty-state"><h2>No wildlife notes yet</h2><p className="muted">Upload a photo to start a sighting record.</p></div>
  }
  return (
    <div className="sighting-grid">
      {detail.sightings.map((sighting) => {
        const media = detail.media.find((item) => item.id === sighting.media_id)
        return (
          <Panel className="sighting-card" key={sighting.id}>
            {media && <img className="sighting-photo" src={mediaUrl(media.id)} alt="" onError={(event) => { event.currentTarget.src = '/mock/misty.svg' }} />}
            <div className="sighting-content"><SightingDetails sighting={sighting} /></div>
          </Panel>
        )
      })}
    </div>
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
