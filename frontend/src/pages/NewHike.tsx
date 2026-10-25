import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { createHike, listHikes, planHike } from '../api/client'
import type { Hike, HikeCard } from '../api/types'
import { ErrorBox, PageLoading, PlanProgressLoader } from '../components/Shared'

function nextSaturday(): string {
  const date = new Date()
  const daysUntilSaturday = (6 - date.getDay() + 7) % 7 || 7
  date.setDate(date.getDate() + daysUntilSaturday)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function NewHike() {
  const navigate = useNavigate()
  const [hikes, setHikes] = useState<HikeCard[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [date, setDate] = useState(nextSaturday())
  const [title, setTitle] = useState('')
  const [titleEdited, setTitleEdited] = useState(false)
  const [hiker, setHiker] = useState('Edouard')
  const [loadingHikes, setLoadingHikes] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [loadError, setLoadError] = useState('')
  const [createdHike, setCreatedHike] = useState<Hike | null>(null)

  const completedHikes = useMemo(() => hikes.filter((hike) => hike.status === 'completed'), [hikes])
  const selected = completedHikes.find((hike) => hike.id === selectedId)
  const autoTitle = selected ? `${selected.trail_name} — ${date}` : ''
  const displayedTitle = titleEdited ? title : autoTitle

  async function loadHikes() {
    try {
      const items = await listHikes()
      const completed = items.filter((hike) => hike.status === 'completed')
      setHikes(completed)
      setSelectedId((current) => current || completed[0]?.id || '')
      setLoadError('')
    } catch (loadError) {
      setLoadError(loadError instanceof Error ? loadError.message : 'Could not load completed hikes.')
    } finally {
      setLoadingHikes(false)
    }
  }

  useEffect(() => { void loadHikes() }, [])

  function retryLoad() {
    setLoadingHikes(true)
    setLoadError('')
    void loadHikes()
  }

  async function handleSubmit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault()
    if (!selected) return
    setSubmitting(true)
    setError('')
    try {
      let hike = createdHike
      if (!hike) {
        hike = await createHike({
          title: title.trim() || autoTitle,
          trail_name: selected.trail_name,
          hiker: hiker.trim() || 'Edouard',
          date,
          status: 'planned',
          based_on_hike_id: selected.id,
        })
        setCreatedHike(hike)
      }
      await planHike(hike.id)
      navigate(`/hikes/${hike.id}?tab=plan`)
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Could not create the plan.')
    } finally {
      setSubmitting(false)
    }
  }

  if (loadingHikes) return <PageLoading />

  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">Plan with a little context</span>
          <h1>A day worth looking forward to.</h1>
          <p className="subheading">Use a completed hike to help estimate pace. The plan is a starting point—always check conditions before you go.</p>
        </div>
      </div>
      {(loadError || error) && (
        <div style={{ maxWidth: 680, margin: '0 auto 16px' }}>
          <ErrorBox
            message={loadError || error}
            retry={loadError ? retryLoad : () => void handleSubmit()}
          />
        </div>
      )}
      {submitting ? (
        <div className="form-panel"><PlanProgressLoader hikeId={createdHike?.id} label="Working on your plan" /></div>
      ) : (
        <form className="panel form-panel" onSubmit={(event) => void handleSubmit(event)}>
          <div className="form-grid">
            {completedHikes.length === 0 ? (
              <div className="empty-state">
                <h2>No completed hikes to base this on.</h2>
                <p className="muted">Add a completed hike first, then come back to plan.</p>
                <Link to="/" className="button">Back to hikes</Link>
              </div>
            ) : (
              <>
                <label>
                  <span className="field-label">Base this on a completed hike</span>
                  <select className="select" value={selectedId} onChange={(event) => {
                    setCreatedHike(null)
                    setSelectedId(event.target.value)
                  }}>
                    {completedHikes.map((hike) => (
                      <option key={hike.id} value={hike.id}>{hike.title} · {hike.trail_name}</option>
                    ))}
                  </select>
                </label>
                <label>
                  <span className="field-label">Planned date</span>
                  <input className="input" type="date" value={date} onChange={(event) => {
                    setCreatedHike(null)
                    setDate(event.target.value)
                  }} required />
                </label>
                <label>
                  <span className="field-label">Hike title</span>
                  <input className="input" value={displayedTitle} onChange={(event) => {
                    setCreatedHike(null)
                    setTitle(event.target.value)
                    setTitleEdited(true)
                  }} required />
                </label>
                <label>
                  <span className="field-label">Hiker name</span>
                  <input className="input" value={hiker} onChange={(event) => {
                    setCreatedHike(null)
                    setHiker(event.target.value)
                  }} required />
                </label>
                <p className="muted small">Past pace helps with timing; it cannot predict the weather or your conditions on the day.</p>
                <div className="form-actions"><button className="button" type="submit">Create plan <span aria-hidden="true">→</span></button></div>
              </>
            )}
          </div>
        </form>
      )}
    </>
  )
}

export default NewHike
