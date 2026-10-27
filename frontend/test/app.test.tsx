import { afterEach, beforeAll, expect, test, vi } from 'vitest'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import App from '../src/App'

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute('open', '')
  }
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute('open')
  }
})
afterEach(cleanup)

test('imports catalogue and supports search, keyboard details and clearing search', async () => {
  render(<App />)
  expect(
    await screen.findByRole('button', {
      name: 'View Portrait of a Saint, Oil on Canvas',
    }),
  ).toBeInTheDocument()
  const search = screen.getByRole('textbox', { name: 'Search' })
  fireEvent.change(search, { target: { value: 'Emerald' } })
  fireEvent.submit(search.closest('form')!)
  const lot = await screen.findByRole('button', {
    name: 'View Emerald Pendant Necklace',
  })
  await waitFor(() =>
    expect(
      screen.queryByRole('button', { name: /View Portrait/ }),
    ).not.toBeInTheDocument(),
  )
  fireEvent.keyDown(lot, { key: 'Enter' })
  expect(
    screen.getByRole('dialog', { name: 'Emerald Pendant Necklace' }),
  ).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Close dialog' }))
  fireEvent.click(screen.getByRole('link', { name: /The Yorknew/ }))
  expect(
    await screen.findByRole('heading', { name: 'Main Categories' }),
  ).toBeInTheDocument()
})

test('login submits to the real FastAPI contract while catalogue uses mocks', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ access_token: 'test-token' }), {
        status: 200,
      }),
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: 'user-1',
          name: 'Cliente Demo',
          role: 'bidder',
          email: 'cliente1@example.com',
        }),
        { status: 200 },
      ),
    )
  vi.stubGlobal('fetch', fetch)
  try {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'cliente1@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'DemoAuction2026!' },
    })
    fireEvent.submit(screen.getByLabelText('Email').closest('form')!)
    expect(await screen.findByText('Cliente Demo')).toBeInTheDocument()
    expect(fetch.mock.calls[0][0]).toBe('/api/auth/token')
    expect(fetch.mock.calls[0][1].body.get('username')).toBe(
      'cliente1@example.com',
    )
    expect(fetch.mock.calls[1][0]).toBe('/api/users/me')
    expect(fetch.mock.calls[1][1].headers.get('Authorization')).toBe(
      'Bearer test-token',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  } finally {
    vi.unstubAllGlobals()
  }
})
