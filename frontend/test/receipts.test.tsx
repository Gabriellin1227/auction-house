import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ReceiptPage from '../src/pages/ReceiptPage'
import Participations from '../src/components/Participations'

const receipt = {
  id: 'receipt-1',
  lot_id: 'lot-1',
  item_title: 'Obra arrematada',
  image: '/api/media/item.jpg',
  source_url: 'https://example.com/art',
  winner_public_id: 'public-bidder-1',
  amount_cents: 8000,
  currency: 'BRL',
  settled_at: '2026-10-28T12:00:00Z',
}
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

test('public receipt loads without login and copies its share link', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(receipt)))
  vi.stubGlobal('fetch', fetch)
  const copy = vi.fn().mockResolvedValue(undefined)
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText: copy },
  })
  render(
    <MemoryRouter initialEntries={['/receipts/receipt-1']}>
      <Routes>
        <Route path="/receipts/:receiptId" element={<ReceiptPage />} />
      </Routes>
    </MemoryRouter>,
  )
  expect(await screen.findByText('Obra arrematada')).toBeInTheDocument()
  expect(screen.getByText('public-bidder-1')).toBeInTheDocument()
  expect(screen.getByText(/80,00/)).toBeInTheDocument()
  expect(fetch.mock.calls[0][0]).toBe('/api/receipts/receipt-1')
  fireEvent.click(screen.getByRole('button', { name: 'Copiar link' }))
  expect(await screen.findByText('Link copiado.')).toBeInTheDocument()
  expect(copy).toHaveBeenCalledWith(window.location.href)
  expect(screen.getByRole('link', { name: 'Consultar lote' })).toHaveAttribute(
    'href',
    '/lots/lot-1',
  )
})

test('participations show winning receipt and distinguish pending closure', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            lot: {
              id: 'lot-1',
              title: 'Obra arrematada',
              status: 'closed',
              closureComplete: true,
            },
            highest_bid_cents: 8000,
            won: true,
            leading: false,
            receipt_id: 'receipt-1',
          },
          {
            lot: {
              id: 'lot-2',
              title: 'Outra obra',
              status: 'closed',
              closureComplete: false,
            },
            highest_bid_cents: 1000,
            won: false,
            leading: true,
            receipt_id: null,
          },
        ]),
      ),
    ),
  )
  render(
    <MemoryRouter>
      <Participations revision={0} />
    </MemoryRouter>,
  )
  expect(await screen.findByText('Arrematado por você')).toBeInTheDocument()
  expect(
    screen.getByRole('link', { name: 'Ver comprovante público' }),
  ).toHaveAttribute('href', '/receipts/receipt-1')
  expect(
    screen.getByText('Prazo encerrado · aguardando liquidação'),
  ).toBeInTheDocument()
})

test('invalid receipt explains the failure without showing made-up data', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Comprovante não encontrado' }), {
        status: 404,
      }),
    ),
  )
  render(
    <MemoryRouter initialEntries={['/receipts/missing']}>
      <Routes>
        <Route path="/receipts/:receiptId" element={<ReceiptPage />} />
      </Routes>
    </MemoryRouter>,
  )
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Comprovante não encontrado',
  )
  expect(
    screen.queryByRole('button', { name: 'Copiar link' }),
  ).not.toBeInTheDocument()
})
