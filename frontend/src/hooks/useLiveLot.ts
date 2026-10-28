import { useEffect, useRef, useState } from 'react'
import { API_BASE, ApiError } from '../api/client'
import { fetchLot, USE_MOCK } from '../api/auction'
import type { BidAccepted, Lot } from '../types'

export function useLiveLot(initial: Lot) {
  const [lot, setLot] = useState(initial)
  const [connection, setConnection] = useState('connecting')
  const version = useRef(initial.version || 0)

  useEffect(() => {
    if (USE_MOCK) return
    let disposed = false
    let unavailable = false
    let socket: WebSocket | null = null
    let retry: ReturnType<typeof setTimeout> | undefined
    let failures = 0
    let fetching = false
    let requested = false
    const apply = (fresh: Lot) => {
      if ((fresh.version || 0) < version.current) return
      version.current = fresh.version || 0
      setLot(fresh)
    }
    async function synchronize() {
      requested = true
      if (fetching) return
      fetching = true
      while (requested && !disposed) {
        requested = false
        try {
          const fresh = await fetchLot(String(initial.id))
          if (!disposed) {
            apply(fresh)
            if (socket?.readyState === WebSocket.OPEN) setConnection('live')
          }
        } catch (error) {
          if (!disposed) {
            setConnection('reconnecting')
            if (error instanceof ApiError && error.status === 404) {
              setLot((current) => ({ ...current, status: 'cancelled' }))
              setConnection('offline')
              unavailable = true
              socket?.close()
            }
          }
        }
      }
      fetching = false
    }
    function connect() {
      if (disposed) return
      const url = new URL(
        `${API_BASE}/ws/lots/${initial.id}`,
        window.location.href,
      )
      url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
      socket = new WebSocket(url)
      socket.onopen = () => {
        failures = 0
        void synchronize()
      }
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          if (message.type === 'ResyncRequired') void synchronize()
          else if (
            message.lot_id === String(initial.id) &&
            Number.isSafeInteger(message.version) &&
            message.version > version.current
          )
            void synchronize()
        } catch {
          void synchronize()
        }
      }
      socket.onclose = (event) => {
        if (disposed || unavailable) return
        if (event.code === 1008) {
          setConnection('offline')
          void synchronize()
          return
        }
        setConnection('reconnecting')
        retry = setTimeout(connect, Math.min(1000 * 2 ** failures++, 15000))
      }
      socket.onerror = () => socket?.close()
    }
    const recover = () => {
      if (document.visibilityState === 'visible') void synchronize()
    }
    connect()
    window.addEventListener('online', recover)
    document.addEventListener('visibilitychange', recover)
    return () => {
      disposed = true
      clearTimeout(retry)
      socket?.close()
      window.removeEventListener('online', recover)
      document.removeEventListener('visibilitychange', recover)
    }
  }, [initial.id])

  function accepted(bid: BidAccepted) {
    if (bid.version < version.current) return
    version.current = bid.version
    setLot((current) => ({
      ...current,
      currentBid: bid.amount_cents,
      bids: bid.sequence,
      endsAt: new Date(bid.ends_at).getTime(),
      status: 'live',
      leaderPublicId: bid.bidder_public_id,
      version: bid.version,
    }))
  }
  return { lot, accepted, connection: USE_MOCK ? 'preview' : connection }
}
