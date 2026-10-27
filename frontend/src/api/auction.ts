// Funções de alto nível usadas pelos componentes.
// Cada uma escolhe entre mock e API real conforme VITE_USE_MOCK.

import { http, setAccessToken } from './client'
import { CATEGORIES, LOTS, delay } from '../data/mock'
import type {
  AuthResponse,
  Category,
  LoginPayload,
  Lot,
  LotsQuery,
  RegisterPayload,
  Stats,
  User,
} from '../types'

export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'

export async function fetchCategories(): Promise<Category[]> {
  if (USE_MOCK) {
    await delay()
    return CATEGORIES
  }
  return http.get<Category[]>('/categories')
}

export async function fetchLots(params: LotsQuery = {}): Promise<Lot[]> {
  if (USE_MOCK) {
    await delay()
    let list = [...LOTS]
    if (params.category)
      list = list.filter((l) => l.category === params.category)
    if (params.q) {
      const q = params.q.toLowerCase()
      list = list.filter((l) =>
        `${l.title} ${l.categoryName}`.toLowerCase().includes(q),
      )
    }
    if (params.sort === 'ending') list.sort((a, b) => a.endsAt - b.endsAt)
    if (params.sort === 'price')
      list.sort((a, b) => b.currentBid - a.currentBid)
    return list
  }
  const entries = Object.entries(params).filter(
    (e): e is [string, string] => typeof e[1] === 'string' && e[1] !== '',
  )
  const qs = new URLSearchParams(entries).toString()
  return http.get<Lot[]>(`/lots${qs ? `?${qs}` : ''}`)
}

export async function fetchStats(): Promise<Stats> {
  if (USE_MOCK) {
    await delay()
    return {
      openLots: LOTS.length,
      valueOnFloor: LOTS.reduce((s, l) => s + l.currentBid, 0),
      bidsPlaced: LOTS.reduce((s, l) => s + l.bids, 0),
      hoursOpen: 24,
    }
  }
  return http.get<Stats>('/stats')
}

// Authentication always uses FastAPI, even with the demonstration catalogue.
export async function signIn(credentials: LoginPayload): Promise<AuthResponse> {
  setAccessToken(null)
  const token = await http.form<{ access_token: string }>(
    '/auth/token',
    new URLSearchParams({
      username: credentials.email,
      password: credentials.password,
    }),
  )
  setAccessToken(token.access_token)
  try {
    return { user: await http.get<User>('/users/me') }
  } catch (error) {
    setAccessToken(null)
    throw error
  }
}

export async function register(data: RegisterPayload): Promise<AuthResponse> {
  await http.post<User>('/users', { ...data, role: data.role || 'bidder' })
  return signIn(data)
}

export const signOut = () => setAccessToken(null)
