import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getHealth, listHikes, mediaUrl } from '../api/client'
import type { Health, HikeCard } from '../api/types'
import { formatDate } from '../components/format'
import { ErrorBox, SkeletonCards, StatusBadge } from '../components/Shared'

function HikesGallery() {
  const navigate = useNavigate()
  const [hikes, setHikes] = useState<HikeCard[]>([])
  const [health, setHealth] = useState<Health | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')

  const load = useCallback(async () => {
    try {
      const [items, status] = await Promise.all([listHikes(), getHealth()])
      setHikes(items)
      setHealth(status)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load hikes.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  function retryLoad() {
    setLoading(true)
    setError('')
    void load()
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    navigate(`/search?q=${encodeURIComponent(query.trim())}`)
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">Your trail journal</span>
          <h1>Every hike, in one place.</h1>
          <p className="subheading">Plans, photographs and little things you noticed along the way.</p>
        </div>
        <Link className="button" to="/new">＋ Plan a hike</Link>
      </div>

      <div className="gallery-toolbar">
        <form className="search-bar" onSubmit={submitSearch}>
          <input
            className="input"
            aria-label="Search your hikes"
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search photos, species, trails…"
            value={query}
          />
          <button className="button button-small" type="submit">Search</button>
        </form>
        <span className={`health-pill ${health?.ok ? '' : 'offline'}`}>
          <span className="health-dot" />
          {health?.ok ? `API ok · ${health.mongo ? 'Mongo ok' : 'Mongo offline'}` : 'API offline'}
          {import.meta.env.VITE_USE_MOCKS === 'true' && <span className="mock-label">mock data</span>}
        </span>
      </div>

      {error && <div className="section"><ErrorBox message={error} retry={retryLoad} /></div>}
      {loading && <SkeletonCards />}
      {!loading && !error && hikes.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">⌁</div>
          <h2>Your next story starts outside.</h2>
          <p className="muted">Create a hike to keep its plan, track and memories together.</p>
          <Link to="/new" className="button">Plan your first hike</Link>
        </div>
      )}
      {!loading && !error && hikes.length > 0 && (
        <div className="hike-grid">
          {hikes.map((hike) => (
            <Link className="hike-card" to={`/hikes/${hike.id}`} key={hike.id}>
              <img
                className="hike-cover"
                src={hike.cover_media_id ? mediaUrl(hike.cover_media_id, 'thumb') : '/mock/chilterns.svg'}
                alt=""
                onError={(event) => { event.currentTarget.src = '/mock/chilterns.svg' }}
              />
              <div className="hike-card-body">
                <div className="card-title-row">
                  <div>
                    <h2 className="card-title">{hike.title}</h2>
                    <p className="trail-name">{hike.trail_name}</p>
                  </div>
                  <StatusBadge status={hike.status} />
                </div>
                <div className="card-meta">
                  <span>◷ {formatDate(hike.date)}</span>
                  {hike.distance_km != null && <span>↔ {hike.distance_km.toFixed(1)} km</span>}
                  {hike.ascent_m != null && <span>↑ {Math.round(hike.ascent_m)} m</span>}
                  <span>✳ {hike.species_count ?? 0} sightings</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </>
  )
}

export default HikesGallery
