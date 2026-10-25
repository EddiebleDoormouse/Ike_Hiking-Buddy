import { useEffect, useState, type HTMLAttributes, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import { getPlanProgress } from '../api/client'
import type { Plan, PlanProgress } from '../api/types'

export function StatusBadge({ status }: { status: string }) {
  const label = status === 'not_applicable'
    ? 'Not applicable'
    : status.replace(/_/g, ' ').replace(/^./, (letter) => letter.toUpperCase())
  return <span className={`badge badge-${status}`}>{label}</span>
}

export function ErrorBox({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="error-box" role="alert">
      <p><strong>Something didn’t work.</strong> {message}</p>
      {retry && <button className="button-quiet" onClick={retry}>Try again</button>}
    </div>
  )
}

export function SkeletonCards({ count = 3 }: { count?: number }) {
  return (
    <div className="hike-grid" aria-label="Loading hikes">
      {Array.from({ length: count }, (_, index) => (
        <div className="hike-card" key={index}>
          <div className="skeleton hike-cover" />
          <div className="hike-card-body">
            <div className="skeleton" style={{ height: 18, width: '65%', marginBottom: 12 }} />
            <div className="skeleton" style={{ height: 12, width: '45%', marginBottom: 18 }} />
            <div className="skeleton" style={{ height: 12, width: '78%' }} />
          </div>
        </div>
      ))}
    </div>
  )
}

export function Panel({
  children,
  className = '',
  ...props
}: HTMLAttributes<HTMLElement> & { children: ReactNode }) {
  return <section className={`panel ${className}`} {...props}>{children}</section>
}

export function MarkdownBlock({ content }: { content: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  )
}

export function StepLoader({ label = 'Preparing your hike' }: { label?: string }) {
  const steps = ['Fetching forecast…', 'Drafting plan…', 'Checking…', 'Revising…']
  const [active, setActive] = useState(0)
  useEffect(() => {
    const timer = window.setInterval(() => setActive((step) => Math.min(step + 1, steps.length - 1)), 1800)
    return () => window.clearInterval(timer)
  }, [steps.length])

  return (
    <Panel className="panel-pad">
      <p className="eyebrow">{label}</p>
      <ul className="loading-steps" aria-live="polite">
        {steps.map((step, index) => (
          <li className={index < active ? 'done' : index === active ? 'current' : ''} key={step}>
            {index < active ? '✓' : index === active ? '◌' : '·'} {step}
          </li>
        ))}
      </ul>
    </Panel>
  )
}

const PROGRESS_POLL_MS = 1000

function sameStep(a: PlanProgress, b: PlanProgress): boolean {
  return a.stage === b.stage && a.message === b.message
}

/** Live list of planner stages, polled from the backend while a plan is generated. */
export function PlanProgressLoader({ hikeId, label }: { hikeId?: string; label: string }) {
  const [history, setHistory] = useState<PlanProgress[]>([])

  useEffect(() => {
    if (!hikeId) return
    let cancelled = false
    async function poll() {
      const progress = await getPlanProgress(hikeId as string)
      if (cancelled || !progress) return
      if (progress.events) {
        setHistory(progress.events.filter((event) => event.stage !== 'idle' && event.stage !== 'queued'))
        return
      }
      if (progress.stage === 'idle' || progress.stage === 'queued') return
      setHistory((steps) => {
        const last = steps.at(-1)
        return last && sameStep(last, progress) ? [...steps.slice(0, -1), progress] : [...steps, progress]
      })
    }
    void poll()
    const timer = window.setInterval(() => void poll(), PROGRESS_POLL_MS)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [hikeId])

  if (history.length === 0) return <StepLoader label={label} />
  const current = history.at(-1)
  const seconds = Math.round((current?.elapsed_ms ?? 0) / 1000)
  return (
    <Panel className="panel-pad">
      <p className="eyebrow">{label}</p>
      <ul className="loading-steps" aria-live="polite">
        {history.map((step, index) => {
          const isCurrent = index === history.length - 1 && step.stage !== 'done'
          const hasFailures = step.stage === 'checks' && (step.failed?.length ?? 0) > 0
          const className = hasFailures ? 'failed' : isCurrent ? 'current' : 'done'
          const marker = hasFailures ? '✕' : isCurrent ? '◌' : '✓'
          return (
            <li className={className} key={`${index}-${step.stage}`}>
              {marker} {step.message}
              {hasFailures && <span className="small"> — {step.failed?.join(', ')}</span>}
            </li>
          )
        })}
      </ul>
      <p className="muted small">Elapsed {seconds} s · Gemini is checking its own plan against the forecast and sources.</p>
    </Panel>
  )
}

export function PageLoading() {
  return (
    <div className="form-panel">
      <div className="skeleton" style={{ height: 34, width: '45%', marginBottom: 13 }} />
      <div className="skeleton" style={{ height: 15, width: '68%', marginBottom: 28 }} />
      <div className="skeleton" style={{ height: 250, width: '100%' }} />
    </div>
  )
}

export function PlanSummary({ plan }: { plan: Plan }) {
  return <MarkdownBlock content={plan.final?.summary_md ?? ''} />
}
