// Contrato entre frontend e backend Python.
// Espelhe estes tipos nos modelos Pydantic (FastAPI) ou serializers (Django/DRF).

export interface Category {
  slug: string
  name: string
  image: string
}

export interface Lot {
  id: number
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

export interface BidResponse {
  ok: boolean
  lotId: number
  amount: number
}
