import { useState } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom'
import BidPanel from '../src/components/BidPanel'
import type { CatalogueNavigation } from '../src/App'
import type { Lot } from '../src/types'

vi.mock('../src/api/auction', () => ({ USE_MOCK: false }))
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})
const user = {
  id: 'private-id',
  public_id: 'public-id',
  name: 'Cliente',
  email: 'cliente@example.com',
  role: 'bidder' as const,
  active: true,
}
const lot: Lot = {
  id: 'lot-id',
  number: '1',
  title: 'Obra',
  category: 'fine-art',
  categoryName: 'Arte',
  image: '',
  currentBid: 8000,
  increment: 1000,
  bids: 0,
  endsAt: Date.now() + 600000,
  status: 'live',
}
function Panel() {
  const [state, setState] = useState(lot)
  return (
    <BidPanel
      lot={state}
      closed={false}
      onAccepted={(bid) =>
        setState({
          ...state,
          currentBid: bid.amount_cents,
          bids: bid.sequence,
          leaderPublicId: bid.bidder_public_id,
        })
      }
    />
  )
}
function setup(account: typeof user | null = user) {
  const requestLogin = vi.fn()
  render(
    <MemoryRouter>
      <Routes>
        <Route
          element={
            <Outlet
              context={
                {
                  user: account,
                  requestLogin,
                  setUser: vi.fn(),
                  selectCategory: vi.fn(),
                } satisfies CatalogueNavigation
              }
            />
          }
        >
          <Route index element={<Panel />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
  return requestLogin
}

test('shows business refusal, then sends cents and confirms leadership', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: 'Saldo disponível insuficiente' }),
        { status: 409 },
      ),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: 'bid-1',
          sequence: 1,
          amount_cents: 8000,
          bidder_public_id: user.public_id,
          extended: true,
        }),
        { status: 201 },
      ),
    )
  vi.stubGlobal('fetch', fetch)
  setup()
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar lance' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Saldo disponível insuficiente',
  )
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({
    amount_cents: 8000,
  })
  expect(fetch.mock.calls[0][0]).toBe('/api/lots/lot-id/bids')
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar lance' }))
  expect(
    await screen.findByText('Você está ganhando este lote.'),
  ).toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('Prazo prorrogado')
  expect(
    screen.queryByRole('button', { name: 'Confirmar lance' }),
  ).not.toBeInTheDocument()
})

test('anonymous bidder opens login instead of submitting', () => {
  const login = setup(null)
  fireEvent.click(screen.getByRole('button', { name: 'Entrar para dar lance' }))
  expect(login).toHaveBeenCalledOnce()
  expect(screen.queryByLabelText('Seu lance (R$)')).not.toBeInTheDocument()
})

test('uncertain network response asks to reconcile before resubmitting', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('network')))
  setup()
  fireEvent.click(screen.getByRole('button', { name: 'Confirmar lance' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'O resultado pode ter sido registrado',
  )
})
