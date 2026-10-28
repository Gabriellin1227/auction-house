// Contrato entre frontend e backend Python.
// Espelhe estes tipos nos modelos Pydantic (FastAPI) ou serializers (Django/DRF).

export interface Category {
  slug: string
  name: string
  image: string
}

export interface Lot {
  id: string | number
  leaderPublicId?: string | null
  version?: number
  status?: string
  startsAt?: number
  increment?: number
  sourceUrl?: string
  attributes?: Record<string, unknown>
  number: string
  title: string
  category: string // slug da categoria
  categoryName: string
  image: string
  currentBid: number
  bids: number
  endsAt: number // timestamp UTC em milissegundos
}

export interface Stats {
  openLots: number
  valueOnFloor: number
  bidsPlaced: number
  hoursOpen: number
}

export interface LotsQuery {
  status?: string
  category?: string
  q?: string
  sort?: 'ending' | 'price'
}

export interface User {
  id: string
  public_id: string
  email: string
  role: 'auctioneer' | 'bidder'
  active: boolean
  name: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload extends LoginPayload {
  role?: 'auctioneer' | 'bidder'
  name: string
}

export interface AuthResponse {
  user: User
}

export interface BidRecord {
  id: string
  bidder_public_id: string
  sequence: number
  amount_cents: number
  accepted_at: string
}

export interface BidAccepted extends BidRecord {
  lot_id: string
  version: number
  ends_at: string
  extended: boolean
}
