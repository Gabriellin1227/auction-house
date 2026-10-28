import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AuditPage from '../src/pages/AuditPage'
import CategoryNav from '../src/components/CategoryNav'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const audit = {
  integrity: 'valid',
  checkpoint_status: 'anchored',
  verified_count: 0,
  checkpoint_sequence: 0,
  head_sequence: 0,
  issues: [],
  history: [],
  next_after: null,
}
function setup(data: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(new Response(JSON.stringify(data))),
  )
  render(
    <MemoryRouter initialEntries={['/lots/lot-1/audit']}>
      <Routes>
        <Route path="/lots/:lotId/audit" element={<AuditPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

test('top bar only shows the seven principal categories', () => {
  render(<CategoryNav active="jewelry" onSelect={vi.fn()} />)
  expect(screen.getAllByRole('button')).toHaveLength(7)
  expect(screen.getByRole('button', { name: 'Joias' })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  expect(screen.queryByText('Como funciona')).not.toBeInTheDocument()
  expect(screen.queryByText('Todos os lotes')).not.toBeInTheDocument()
})

test('public audit reports an authenticated and anchored empty history', async () => {
  setup(audit)
  expect(
    await screen.findByRole('heading', {
      name: 'Histórico íntegro e ancorado',
    }),
  ).toBeInTheDocument()
  expect(screen.getByText('Nenhum lance nesta página.')).toBeInTheDocument()
})

test('pending checkpoints never claim the history is fully anchored', async () => {
  setup({ ...audit, checkpoint_status: 'pending', checkpoint_sequence: null })
  expect(
    await screen.findByText('Cadeia válida · checkpoint pendente'),
  ).toBeInTheDocument()
  expect(
    screen.queryByText('Histórico íntegro e ancorado'),
  ).not.toBeInTheDocument()
})

test('tampering is shown clearly to anonymous visitors', async () => {
  setup({
    ...audit,
    integrity: 'invalid',
    checkpoint_status: 'invalid',
    issues: ['Cabeçalho não corresponde ao histórico'],
  })
  expect(
    await screen.findByText('Inconsistência detectada'),
  ).toBeInTheDocument()
  expect(
    screen.getByText('Cabeçalho não corresponde ao histórico'),
  ).toBeInTheDocument()
})
