import { expect, test } from 'vitest'
import { mediaUrl } from '../src/api/client'

test('persisted images use the configured API domain', () => {
  expect(mediaUrl('/api/media/item.jpg', 'https://yorknew.onrender.com')).toBe(
    'https://yorknew.onrender.com/media/item.jpg',
  )
  expect(mediaUrl('/api/media/item.jpg', 'https://example.com/api/')).toBe(
    'https://example.com/api/media/item.jpg',
  )
  expect(mediaUrl('/api/media/item.jpg', '/api')).toBe('/api/media/item.jpg')
})

test('category assets and external catalogue images keep their own paths', () => {
  expect(
    mediaUrl('/images/categories/jewelry.jpg', 'https://api.example.com'),
  ).toBe('/images/categories/jewelry.jpg')
  expect(mediaUrl('https://museum.example.com/image.jpg')).toBe(
    'https://museum.example.com/image.jpg',
  )
})
