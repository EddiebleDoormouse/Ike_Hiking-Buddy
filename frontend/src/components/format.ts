import type { Sighting } from '../api/types'

export function formatDate(value: string | null | undefined): string {
  if (!value) return 'Date not set'
  const date = new Date(`${value.slice(0, 10)}T12:00:00`)
  if (Number.isNaN(date.valueOf())) return 'Date not set'
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(date)
}

export function formatDuration(seconds: number | null | undefined): string | null {
  if (seconds == null || !Number.isFinite(seconds)) return null
  const totalMinutes = Math.round(seconds / 60)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return `${hours}:${String(minutes).padStart(2, '0')}`
}

export function formatLeaveBy(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.valueOf())) return 'Time not available'
  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/London',
  }).format(date)
}

export function getSightingName(sighting: Sighting): { common: string; scientific: string | null } {
  const candidate = sighting.verification.chosen ?? sighting.candidates[0] ?? null
  return candidate
    ? { common: candidate.common_name, scientific: candidate.scientific_name }
    : { common: 'Unidentified', scientific: null }
}
