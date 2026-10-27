// Dados fictícios usados quando VITE_USE_MOCK=true.
// O formato aqui É o contrato esperado do backend Python (veja o README).

import type { Category, Lot } from '../types'

const now = Date.now()
const inMs = (h: number, m = 0, s = 0) => now + ((h * 60 + m) * 60 + s) * 1000

export const CATEGORIES: Category[] = [
  { slug: 'jewelry', name: 'Jewelry', image: '/images/placeholder.svg' },
  { slug: 'fine-art', name: 'Fine Art', image: '/images/placeholder.svg' },
  { slug: 'horology', name: 'Horology', image: '/images/placeholder.svg' },
  { slug: 'ceramics', name: 'Ceramics', image: '/images/placeholder.svg' },
  { slug: 'furniture', name: 'Furniture', image: '/images/placeholder.svg' },
  {
    slug: 'coins-manuscripts',
    name: 'Coins & Manuscripts',
    image: '/images/placeholder.svg',
  },
  {
    slug: 'curiosities',
    name: 'Curiosities',
    image: '/images/placeholder.svg',
  },
]

export const LOTS: Lot[] = [
  {
    id: 1,
    number: '001',
    title: 'Emerald Pendant Necklace',
    category: 'jewelry',
    categoryName: 'Jewelry',
    image: '/images/placeholder.svg',
    currentBid: 880000,
    bids: 0,
    endsAt: inMs(10, 12, 0),
  },
  {
    id: 2,
    number: '002',
    title: 'Engraved Gold Hunter Pocket Watch',
    category: 'horology',
    categoryName: 'Horology',
    image: '/images/placeholder.svg',
    currentBid: 120000,
    bids: 0,
    endsAt: inMs(12, 30, 0),
  },
  {
    id: 3,
    number: '003',
    title: 'Gilded Aviary Amphora',
    category: 'ceramics',
    categoryName: 'Ceramics',
    image: '/images/placeholder.svg',
    currentBid: 236000,
    bids: 0,
    endsAt: inMs(2, 4, 9),
  },
  {
    id: 4,
    number: '004',
    title: 'Twin Relic Display Case',
    category: 'curiosities',
    categoryName: 'Curiosities',
    image: '/images/placeholder.svg',
    currentBid: 16200,
    bids: 0,
    endsAt: inMs(7, 4, 9),
  },
  {
    id: 5,
    number: '005',
    title: 'Hoard of Antique Gold Coins',
    category: 'coins-manuscripts',
    categoryName: 'Coins & Manuscripts',
    image: '/images/placeholder.svg',
    currentBid: 43000,
    bids: 0,
    endsAt: inMs(15, 0, 0),
  },
  {
    id: 8,
    number: '008',
    title: 'Portrait of a Saint, Oil on Canvas',
    category: 'fine-art',
    categoryName: 'Fine Art',
    image: '/images/placeholder.svg',
    currentBid: 700000,
    bids: 0,
    endsAt: inMs(0, 9, 57),
  },
  {
    id: 9,
    number: '009',
    title: 'Carved Mahogany Salon Throne',
    category: 'furniture',
    categoryName: 'Furniture',
    image: '/images/placeholder.svg',
    currentBid: 32000,
    bids: 0,
    endsAt: inMs(5, 9, 57),
  },
]

export const delay = (ms = 250) => new Promise<void>((r) => setTimeout(r, ms))
