import { afterEach, beforeAll, beforeEach, expect, test, vi } from 'vitest'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import App from '../src/App'

beforeEach(() => {
  window.history.replaceState({}, '', '/')
})
beforeAll(() => {
  window.scrollTo = vi.fn()
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute('open', '')
  }
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute('open')
  }
})
afterEach(cleanup)

test('navigates to lot page, keeps header mounted and preserves search on return', async () => {
  render(<App />)
  expect(
    await screen.findByRole('link', {
      name: 'View Portrait of a Saint, Oil on Canvas',
    }),
  ).toBeInTheDocument()
  const search = screen.getByRole('textbox', { name: 'Search' })
  fireEvent.change(search, { target: { value: 'Emerald' } })
  fireEvent.submit(search.closest('form')!)
  const lot = await screen.findByRole('link', {
    name: 'View Emerald Pendant Necklace',
  })
  await waitFor(() =>
    expect(
      screen.queryByRole('link', { name: /View Portrait/ }),
    ).not.toBeInTheDocument(),
  )
  const header = screen.getByRole('banner')
  fireEvent.click(lot)
  expect(
    await screen.findByRole('heading', {
      level: 1,
      name: 'Emerald Pendant Necklace',
    }),
  ).toBeInTheDocument()
  expect(window.location.pathname).toBe('/lots/1')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(screen.getByRole('banner')).toBe(header)
  fireEvent.click(screen.getByRole('link', { name: 'Vitrine' }))
  expect(window.location.search).toBe('?q=Emerald')
  expect(
    await screen.findByRole('link', { name: 'View Emerald Pendant Necklace' }),
  ).toBeInTheDocument()
  fireEvent.click(screen.getByRole('link', { name: /The Yorknew/ }))
  expect(
    await screen.findByRole('heading', { name: 'Categorias Principais' }),
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
    fireEvent.click(screen.getByRole('button', { name: 'Login' }))
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
    fireEvent.click(screen.getByRole('button', { name: 'Sair' }))
    expect(screen.getByRole('button', { name: 'Login' })).toBeInTheDocument()
  } finally {
    vi.unstubAllGlobals()
  }
})

test('opens a lot directly from its URL and preserves the header on browser back', async () => {
  window.history.replaceState({}, '', '/lots/8')
  render(<App />)
  expect(
    await screen.findByRole('heading', {
      level: 1,
      name: 'Portrait of a Saint, Oil on Canvas',
    }),
  ).toBeInTheDocument()
  const header = screen.getByRole('banner')
  fireEvent.click(screen.getByRole('link', { name: /The Yorknew/ }))
  expect(
    await screen.findByRole('heading', { name: 'Categorias Principais' }),
  ).toBeInTheDocument()
  window.history.back()
  expect(
    await screen.findByRole('heading', {
      level: 1,
      name: 'Portrait of a Saint, Oil on Canvas',
    }),
  ).toBeInTheDocument()
  expect(screen.getByRole('banner')).toBe(header)
})

test('unknown lot shows a recovery link and the shared header', async () => {
  window.history.replaceState({}, '', '/lots/unknown')
  render(<App />)
  expect(
    await screen.findByRole('heading', { name: 'Lote não encontrado' }),
  ).toBeInTheDocument()
  expect(screen.getByRole('banner')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('link', { name: 'Voltar à vitrine' }))
  expect(
    await screen.findByRole('heading', { name: 'Categorias Principais' }),
  ).toBeInTheDocument()
})

test('translated category navigation uses catalogue IDs and updates the URL', async () => {
  render(<App />)
  fireEvent.click(screen.getByRole('button', { name: 'Joias' }))
  expect(window.location.search).toBe('?category=jewelry')
  expect(
    await screen.findByRole('link', { name: 'View Emerald Pendant Necklace' }),
  ).toBeInTheDocument()
  expect(
    screen.queryByRole('link', { name: /View Portrait/ }),
  ).not.toBeInTheDocument()
})
