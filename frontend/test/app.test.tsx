import { afterEach, beforeAll, beforeEach, expect, test, vi } from 'vitest'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import App from '../src/App'

// Navigation assertions don't depend on the demo's simulated network latency.
vi.mock('../src/data/mock', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/data/mock')>()
  return { ...actual, delay: () => Promise.resolve() }
})

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
      name: 'Ver Retrato de um santo, óleo sobre tela',
    }),
  ).toBeInTheDocument()
  const search = screen.getByRole('textbox', { name: 'Buscar' })
  fireEvent.change(search, { target: { value: 'Esmeralda' } })
  fireEvent.submit(search.closest('form')!)
  const lot = await screen.findByRole('link', {
    name: 'Ver Colar com pingente de esmeralda',
  })
  await waitFor(() =>
    expect(
      screen.queryByRole('link', { name: /Ver Retrato/ }),
    ).not.toBeInTheDocument(),
  )
  const header = screen.getByRole('banner')
  fireEvent.click(lot)
  expect(
    await screen.findByRole('heading', {
      level: 1,
      name: 'Colar com pingente de esmeralda',
    }),
  ).toBeInTheDocument()
  expect(window.location.pathname).toBe('/lots/1')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(screen.getByRole('banner')).toBe(header)
  fireEvent.click(screen.getByRole('link', { name: 'Vitrine' }))
  expect(window.location.search).toBe('?q=Esmeralda')
  expect(
    await screen.findByRole('link', {
      name: 'Ver Colar com pingente de esmeralda',
    }),
  ).toBeInTheDocument()
  fireEvent.click(screen.getByRole('link', { name: /The Yorknew/ }))
  expect(
    await screen.findByRole('heading', { name: 'Categorias principais' }),
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
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    fireEvent.change(screen.getByLabelText('E-mail'), {
      target: { value: 'cliente1@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'DemoAuction2026!' },
    })
    fireEvent.submit(screen.getByLabelText('E-mail').closest('form')!)
    expect(
      await screen.findByRole('link', { name: /Minha conta.*Cliente Demo/ }),
    ).toBeInTheDocument()
    expect(fetch.mock.calls[0][0]).toBe('/api/auth/token')
    expect(fetch.mock.calls[0][1].body.get('username')).toBe(
      'cliente1@example.com',
    )
    expect(fetch.mock.calls[1][0]).toBe('/api/users/me')
    expect(fetch.mock.calls[1][1].headers.get('Authorization')).toBe(
      'Bearer test-token',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Sair' }))
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeInTheDocument()
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
      name: 'Retrato de um santo, óleo sobre tela',
    }),
  ).toBeInTheDocument()
  const header = screen.getByRole('banner')
  fireEvent.click(screen.getByRole('link', { name: /The Yorknew/ }))
  expect(
    await screen.findByRole('heading', { name: 'Categorias principais' }),
  ).toBeInTheDocument()
  window.history.back()
  expect(
    await screen.findByRole('heading', {
      level: 1,
      name: 'Retrato de um santo, óleo sobre tela',
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
    await screen.findByRole('heading', { name: 'Categorias principais' }),
  ).toBeInTheDocument()
})

test('translated category navigation uses catalogue IDs and updates the URL', async () => {
  render(<App />)
  fireEvent.click(screen.getByRole('button', { name: 'Joias' }))
  expect(window.location.search).toBe('?category=jewelry')
  expect(
    await screen.findByRole('link', {
      name: 'Ver Colar com pingente de esmeralda',
    }),
  ).toBeInTheDocument()
  expect(
    screen.queryByRole('link', { name: /Ver Retrato/ }),
  ).not.toBeInTheDocument()
})

test('account page submits simulated deposit with idempotency and refreshes balance', async () => {
  let balance = 0
  const fetch = vi.fn(async (path: string, options?: RequestInit) => {
    let data: unknown
    if (path.endsWith('/auth/token')) data = { access_token: 'test-token' }
    else if (path.endsWith('/users/me'))
      data = {
        id: 'user-1',
        name: 'Cliente Demo',
        email: 'cliente1@example.com',
        role: 'bidder',
        active: true,
      }
    else if (
      path.endsWith('/wallets/me/entries') ||
      path.includes('/bidders/me/participations')
    )
      data = []
    else if (path.endsWith('/wallets/me/deposits')) {
      expect(JSON.parse(String(options?.body)).amount_cents).toBe(10000)
      expect(new Headers(options?.headers).get('Idempotency-Key')).toBeTruthy()
      balance = 10000
      data = {
        balance_cents: balance,
        reserved_cents: 0,
        available_cents: balance,
      }
    } else
      data = {
        balance_cents: balance,
        reserved_cents: 0,
        available_cents: balance,
      }
    return new Response(JSON.stringify(data), { status: 200 })
  })
  vi.stubGlobal('fetch', fetch)
  try {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Entrar' }))
    fireEvent.change(screen.getByLabelText('E-mail'), {
      target: { value: 'cliente1@example.com' },
    })
    fireEvent.change(screen.getByLabelText('Senha'), {
      target: { value: 'DemoAuction2026!' },
    })
    fireEvent.submit(screen.getByLabelText('E-mail').closest('form')!)
    fireEvent.click(
      await screen.findByRole('link', { name: /Minha conta.*Cliente Demo/ }),
    )
    expect(
      await screen.findByRole('heading', { name: 'Minha carteira' }),
    ).toBeInTheDocument()
    const amount = screen.getByLabelText('Depósito simulado (R$)')
    fireEvent.change(amount, { target: { value: '100' } })
    fireEvent.submit(amount.closest('form')!)
    expect(
      await screen.findByText('Depósito simulado registrado.'),
    ).toBeInTheDocument()
    expect((await screen.findAllByText(/100,00/)).length).toBeGreaterThan(0)
  } finally {
    vi.unstubAllGlobals()
  }
})
