import { useEffect, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { mediaUrl, search } from '../api/client'
import type { SearchResult } from '../api/types'
import { ErrorBox, SkeletonCards, StatusBadge } from '../components/Shared'

const examples = ['fox', 'red mushrooms', 'misty views']

function SearchPage() {
  const [params, setParams] = useSearchParams()
  const initialQuery = params.get('q') ?? ''

  return (
    <SearchContent
      key={initialQuery}
      initialQuery={initialQuery}
      onSearch={(query) => setParams(query ? { q: query } : {})}
    />
  )
}

function SearchContent({
  initialQuery,
  onSearch,
}: {
  initialQuery: string
  onSearch: (query: string) => void
}) {
  const [query, setQuery] = useState(initialQuery)
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(Boolean(initialQuery.trim()))
  const [error, setError] = useState('')
  const [retryCount, setRetryCount] = useState(0)

  useEffect(() => {
    const searchQuery = initialQuery.trim()
    if (!searchQuery) return

    let active = true
    search(searchQuery)
      .then((items) => { if (active) setResults(items) })
      .catch((searchError: unknown) => {
        if (active) setError(searchError instanceof Error ? searchError.message : 'Search could not be completed.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [initialQuery, retryCount])

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nextQuery = query.trim()
    if (nextQuery === initialQuery) {
      setResults([])
      setError('')
      setLoading(Boolean(nextQuery))
      setRetryCount((count) => count + 1)
    } else {
      onSearch(nextQuery)
    }
  }

  function chooseExample(value: string) {
    setQuery(value)
    onSearch(value)
  }

  function retrySearch() {
    setResults([])
    setError('')
    setLoading(true)
    setRetryCount((count) => count + 1)
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">Find a memory</span>
          <h1>Search your hikes.</h1>
          <p className="subheading">Look across captions, notes and wildlife suggestions. Identification results are not certainty.</p>
        </div>
      </div>
      <form className="search-bar" onSubmit={submit}>
        <input
          className="input"
          aria-label="Search your hikes"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Try a species, place or moment…"
          value={query}
        />
        <button className="button" type="submit">Search</button>
      </form>
      <div className="query-chips" aria-label="Example searches">
        {examples.map((example) => (
          <button className="query-chip" key={example} onClick={() => chooseExample(example)} type="button">
            {example}
          </button>
        ))}
      </div>
      {error && <ErrorBox message={error} retry={retrySearch} />}
      {loading && <SkeletonCards />}
      {!loading && !error && !initialQuery.trim() && (
        <div className="empty-state">
          <div className="empty-icon">⌕</div>
          <h2>A detail you remember?</h2>
          <p className="muted">Search above, or pick one of the example phrases.</p>
        </div>
      )}
      {!loading && !error && initialQuery.trim() && results.length === 0 && (
        <div className="empty-state">
          <h2>No matching memories yet.</h2>
          <p className="muted">Try another phrase, such as “fox” or “misty views”.</p>
        </div>
      )}
      {!loading && !error && results.length > 0 && (
        <div className="result-grid">
          {results.map((result) => {
            const sighting = result.sighting
            const image = result.media.kind === 'photo' ? mediaUrl(result.media.id, 'thumb') : '/mock/misty.svg'
            return (
              <article className="panel result-card" key={result.media.id}>
                <Link to={`/hikes/${result.media.hike_id}?tab=media`}>
                  <img className="media-image" src={image} alt="" onError={(event) => { event.currentTarget.src = '/mock/misty.svg' }} />
                </Link>
                <div className="result-body">
                  <Link className="result-hike" to={`/hikes/${result.media.hike_id}`}>{result.hike_title}</Link>
                  <p className="media-caption" style={{ padding: 0 }}>{result.media.caption || result.media.text || result.media.filename}</p>
                  {sighting && (
                    <>
                      <div style={{ marginTop: 9 }}><StatusBadge status={sighting.verification.status} /></div>
                      {sighting.verification.chosen && (
                        <p className="confidence-line">
                          Confidence · <strong>{Math.round(sighting.verification.chosen.confidence * 100)}%</strong>
                        </p>
                      )}
                      <p className="specialist-line">
                        Why · {sighting.verification.reasons[0] || 'No explanation was provided for this suggestion.'}
                      </p>
                    </>
                  )}
                  <p className="result-score">Match score · {Math.round(result.score * 100)}%</p>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </>
  )
}

export default SearchPage
