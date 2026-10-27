import { useEffect, useState } from 'react'

/** Retorna "0h 09m 57s" a partir de um timestamp (ms) de encerramento. */
export function useCountdown(endsAt: number): {
  label: string
  closed: boolean
} {
  const [left, setLeft] = useState(() => Math.max(0, endsAt - Date.now()))

  useEffect(() => {
    const tick = () => setLeft(Math.max(0, endsAt - Date.now()))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [endsAt])

  const total = Math.floor(left / 1000)
  const h = Math.floor(total / 3600)
  const m = String(Math.floor((total % 3600) / 60)).padStart(2, '0')
  const s = String(total % 60).padStart(2, '0')

  return {
    label: left === 0 ? 'Closed' : `${h}h ${m}m ${s}s`,
    closed: left === 0,
  }
}
