import { useEffect, useState, type HTMLAttributes, type ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import type { Plan } from '../api/types'

export function StatusBadge({ status }: { status: string }) {
  const label = status === 'not_applicable' ? 'Not applicable' : status
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
