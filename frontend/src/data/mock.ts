// Dados fictícios usados quando VITE_USE_MOCK=true.
// O formato aqui É o contrato esperado do backend Python (veja o README).

import type { Category, Lot } from '../types'

const now = Date.now()
const inMs = (h: number, m = 0, s = 0) => now + ((h * 60 + m) * 60 + s) * 1000

export const CATEGORIES: Category[] = [
  { slug: 'jewelry', name: 'Joias', image: '/images/placeholder.svg' },
  { slug: 'fine-art', name: 'Belas-artes', image: '/images/placeholder.svg' },
  { slug: 'horology', name: 'Relojoaria', image: '/images/placeholder.svg' },
  { slug: 'ceramics', name: 'Cerâmica', image: '/images/placeholder.svg' },
  { slug: 'furniture', name: 'Mobília', image: '/images/placeholder.svg' },
  {
    slug: 'coins-manuscripts',
    name: 'Moedas e manuscritos',
    image: '/images/placeholder.svg',
  },
  {
    slug: 'curiosities',
    name: 'Curiosidades',
    image: '/images/placeholder.svg',
  },
]

export const LOTS: Lot[] = [
  {
    id: 1,
    number: '001',
    title: 'Colar com pingente de esmeralda',
    category: 'jewelry',
    categoryName: 'Joias',
    image: '/images/placeholder.svg',
    currentBid: 880000,
    bids: 0,
    endsAt: inMs(10, 12, 0),
  },
  {
    id: 2,
    number: '002',
    title: 'Relógio de bolso dourado gravado',
    category: 'horology',
    categoryName: 'Relojoaria',
    image: '/images/placeholder.svg',
    currentBid: 120000,
    bids: 0,
    endsAt: inMs(12, 30, 0),
  },
  {
    id: 3,
    number: '003',
    title: 'Ânfora dourada com aves',
    category: 'ceramics',
    categoryName: 'Cerâmica',
    image: '/images/placeholder.svg',
    currentBid: 236000,
    bids: 0,
    endsAt: inMs(2, 4, 9),
  },
  {
    id: 4,
    number: '004',
    title: 'Vitrine para relíquias',
    category: 'curiosities',
    categoryName: 'Curiosidades',
    image: '/images/placeholder.svg',
    currentBid: 16200,
    bids: 0,
    endsAt: inMs(7, 4, 9),
  },
  {
    id: 5,
    number: '005',
    title: 'Coleção de moedas antigas de ouro',
    category: 'coins-manuscripts',
    categoryName: 'Moedas e manuscritos',
    image: '/images/placeholder.svg',
    currentBid: 43000,
    bids: 0,
    endsAt: inMs(15, 0, 0),
  },
  {
    id: 8,
    number: '008',
    title: 'Retrato de um santo, óleo sobre tela',
    category: 'fine-art',
    categoryName: 'Belas-artes',
    image: '/images/placeholder.svg',
    currentBid: 700000,
    bids: 0,
    endsAt: inMs(0, 9, 57),
  },
  {
    id: 9,
    number: '009',
    title: 'Poltrona de mogno entalhada',
    category: 'furniture',
    categoryName: 'Mobília',
    image: '/images/placeholder.svg',
    currentBid: 32000,
    bids: 0,
    endsAt: inMs(5, 9, 57),
  },
]

export const delay = (ms = 250) => new Promise<void>((r) => setTimeout(r, ms))
