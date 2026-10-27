import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
test('renderiza React com matchers DOM', () => {
  render(<button type="button">Dar lance</button>)
  expect(screen.getByRole('button', { name: 'Dar lance' })).toBeEnabled()
})
