import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getHealth, listHikes, mediaUrl } from '../api/client'
import type { Health, HikeCard } from '../api/types'
import { Masonry, type BoardEntry } from '../components/Board'
import { formatDate } from '../components/format'
import { ErrorBox, SkeletonCards } from '../components/Shared'

type Filter = 'all' | 'completed' | 'planned'

function HikesGallery() {
  const navigate = useNavigate()
  const [hikes, setHikes] = useState<HikeCard[]>([])
  const [health, setHealth] = useState<Health | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<Filter>('all')

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

  useEffect(() => { void load() }, [load])

  function retryLoad() {
    setLoading(true)
    setError('')
    void load()
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (query.trim()) navigate(`/search?q=${encodeURIComponent(query.trim())}`)
  }

  const shown = hikes.filter((hike) => filter === 'all' || hike.status === filter)
  const counts = {
    all: hikes.length,
    completed: hikes.filter((hike) => hike.status === 'completed').length,
    planned: hikes.filter((hike) => hike.status === 'planned').length,
  }

  const entries: BoardEntry[] = [
    {
      key: 'new',
      weight: 0.55,
      node: (
        <Link className="tile tile-new" to="/new">
          <span className="tile-new-plus" aria-hidden="true">+</span>
          <span>Plan a new hike</span>
          <span className="tile-new-hint">Forecast, daylight and kit, checked</span>
        </Link>
      ),
    },
    ...shown.map((hike, index): BoardEntry => ({
      key: hike.id,
      weight: index % 3 === 1 ? 1.15 : 0.95,
      node: (
        <Link className="hike-tile" to={`/hikes/${hike.id}`}>
          <div className={`hike-tile-cover ${index % 3 === 1 ? 'tall' : ''}`}>
            <img
              src={hike.cover_media_id ? mediaUrl(hike.cover_media_id, 'thumb') : '/mock/chilterns.svg'}
              alt=""
              loading="lazy"
              onError={(event) => { event.currentTarget.src = '/mock/chilterns.svg' }}
            />
            {hike.status === 'planned' && <span className="cover-flag">Planned</span>}
          </div>
          <div className="hike-tile-text">
            <h2>{hike.title}</h2>
            <p>{hike.trail_name}</p>
            <p className="hike-tile-facts">
              <span>{formatDate(hike.date)}</span>
              {hike.distance_km != null && <span>{hike.distance_km.toFixed(1)} km</span>}
              {hike.ascent_m != null && <span>{Math.round(hike.ascent_m)} m up</span>}
              {(hike.species_count ?? 0) > 0 && <span>{hike.species_count} species</span>}
            </p>
          </div>
        </Link>
      ),
    })),
  ]

  return (
    <>
      <form className="hero-search" onSubmit={submitSearch} role="search">
        <label htmlFor="hero-q" className="sr-only">Search your hikes</label>
        <input
          id="hero-q"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search your trails…"
          value={query}
          autoComplete="off"
        />
        <p className="hero-search-hint">A fox, red mushrooms, that misty ridge. Search remembers what your photos show.</p>
      </form>

      <div className="board-bar">
        <div className="filter-chips" role="tablist" aria-label="Filter hikes">
          {(['all', 'completed', 'planned'] as Filter[]).map((key) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={filter === key}
              className={`chip ${filter === key ? 'on' : ''}`}
              onClick={() => setFilter(key)}
            >
              {key === 'all' ? 'All hikes' : key === 'completed' ? 'Walked' : 'Planned'}
              <span className="chip-count">{counts[key]}</span>
            </button>
          ))}
        </div>
        <span className={`health-pill ${health?.ok ? '' : 'offline'}`} title="Backend status">
          <span className="health-dot" />
          {health?.ok ? (health.mongo ? 'Synced with Atlas' : 'Atlas offline') : 'Offline'}
          {import.meta.env.VITE_USE_MOCKS === 'true' && <span className="mock-label">sample data</span>}
        </span>
      </div>

      {error && <ErrorBox message={error} retry={retryLoad} />}
      {loading && <SkeletonCards count={6} />}
      {!loading && !error && <Masonry items={entries} />}
    </>
  )
}

export default HikesGallery
