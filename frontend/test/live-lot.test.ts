import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { fetchLot } from '../src/api/auction'
import { useLiveLot } from '../src/hooks/useLiveLot'
import type { BidAccepted, Lot } from '../src/types'

vi.mock('../src/api/auction', () => ({ USE_MOCK: false, fetchLot: vi.fn() }))

class TestSocket {
  static OPEN = 1
  static instances: TestSocket[] = []
  readyState = 0
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: ((event: { code: number }) => void) | null = null
  onerror: (() => void) | null = null
  constructor(public url: URL) {
    TestSocket.instances.push(this)
  }
  open() {
    this.readyState = 1
    this.onopen?.()
  }
  message(value: unknown) {
    this.onmessage?.({ data: JSON.stringify(value) })
  }
  close() {
    this.readyState = 3
    this.onclose?.({ code: 1000 })
  }
  disconnect() {
    this.readyState = 3
    this.onclose?.({ code: 1006 })
  }
}
const initial: Lot = {
  id: 'lot-1',
  number: '1',
  title: 'Obra',
  category: 'fine-art',
  categoryName: 'Arte',
  image: '',
  currentBid: 8000,
  increment: 1000,
  bids: 0,
  endsAt: Date.now() + 600000,
  version: 0,
}
beforeEach(() => {
  TestSocket.instances = []
  vi.mocked(fetchLot).mockReset()
  vi.stubGlobal('WebSocket', TestSocket)
})
afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

test('synchronizes on connect, deduplicates versions and keeps newer HTTP acceptance', async () => {
  vi.mocked(fetchLot)
    .mockResolvedValueOnce(initial)
    .mockResolvedValueOnce({
      ...initial,
      version: 2,
      currentBid: 9000,
      bids: 2,
    })
    .mockResolvedValueOnce({
      ...initial,
      version: 3,
      currentBid: 10000,
      bids: 3,
    })
  const { result } = renderHook(() => useLiveLot(initial))
  const socket = TestSocket.instances[0]
  expect(socket.url.pathname).toBe('/api/ws/lots/lot-1')
  act(() => socket.open())
  await waitFor(() => expect(result.current.connection).toBe('live'))
  act(() =>
    socket.message({ type: 'BidAccepted', lot_id: 'lot-1', version: 2 }),
  )
  await waitFor(() => expect(result.current.lot.currentBid).toBe(9000))
  act(() => {
    socket.message({ type: 'AuctionExtended', lot_id: 'lot-1', version: 2 })
    socket.message({ type: 'BidAccepted', lot_id: 'lot-1', version: 1 })
    socket.message({ type: 'BidAccepted', lot_id: 'another-lot', version: 9 })
  })
  expect(fetchLot).toHaveBeenCalledTimes(2)
  act(() =>
    result.current.accepted({
      version: 4,
      amount_cents: 11000,
      sequence: 4,
      ends_at: new Date(initial.endsAt).toISOString(),
      bidder_public_id: 'public-1',
    } as BidAccepted),
  )
  act(() =>
    socket.message({ type: 'BidAccepted', lot_id: 'lot-1', version: 5 }),
  )
  await waitFor(() => expect(fetchLot).toHaveBeenCalledTimes(3))
  expect(result.current.lot.currentBid).toBe(11000)
  expect(result.current.lot.version).toBe(4)
})

test('reconnects and recovers bids missed while offline, closing on unmount', async () => {
  vi.mocked(fetchLot)
    .mockResolvedValueOnce(initial)
    .mockResolvedValueOnce({
      ...initial,
      currentBid: 12000,
      version: 5,
      bids: 5,
    })
  const { result, unmount } = renderHook(() => useLiveLot(initial))
  act(() => TestSocket.instances[0].open())
  await waitFor(() => expect(result.current.connection).toBe('live'))
  vi.useFakeTimers()
  act(() => TestSocket.instances[0].disconnect())
  expect(result.current.connection).toBe('reconnecting')
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1000)
  })
  expect(TestSocket.instances).toHaveLength(2)
  await act(async () => TestSocket.instances[1].open())
  expect(result.current.lot.currentBid).toBe(12000)
  expect(result.current.connection).toBe('live')
  unmount()
  expect(TestSocket.instances[1].readyState).toBe(3)
  await vi.advanceTimersByTimeAsync(30000)
  expect(TestSocket.instances).toHaveLength(2)
})

test('resync repairs state even without a newer version', async () => {
  vi.mocked(fetchLot)
    .mockResolvedValueOnce(initial)
    .mockResolvedValueOnce({
      ...initial,
      status: 'live',
    })
  const { result } = renderHook(() =>
    useLiveLot({ ...initial, status: 'scheduled' }),
  )
  act(() => TestSocket.instances[0].open())
  await waitFor(() => expect(result.current.connection).toBe('live'))
  act(() =>
    TestSocket.instances[0].message({
      type: 'ResyncRequired',
      reason: 'heartbeat',
    }),
  )
  await waitFor(() => expect(result.current.lot.status).toBe('live'))
})
