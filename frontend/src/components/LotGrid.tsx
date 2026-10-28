import { fetchLots } from '../api/auction'
import { useAsync } from '../hooks/useAsync'
import LotCard from './LotCard'
import SectionTitle from './SectionTitle'
import type { LotsQuery } from '../types'

interface LotGridProps {
  eyebrow?: string
  title: string
  params: LotsQuery
  limit?: number
}

export default function LotGrid({
  eyebrow,
  title,
  params,
  limit,
}: LotGridProps) {
  const key = JSON.stringify(params)
  const {
    data: lots,
    loading,
    error,
  } = useAsync(() => fetchLots(params), [key])
  const visible = limit ? lots?.slice(0, limit) : lots

  return (
    <section className="section">
      <div className="container">
        <SectionTitle eyebrow={eyebrow} title={title} />
        {error && (
          <p className="muted">
            Não foi possível carregar os lotes. {error.message}
          </p>
        )}
        {loading && <p className="muted">Carregando...</p>}
        {!loading && !error && visible?.length === 0 && (
          <p className="muted">Não foram encontrados lotes.</p>
        )}
        <div className="lotgrid">
          {visible?.map((lot) => (
            <LotCard key={lot.id} lot={lot} />
          ))}
        </div>
      </div>
    </section>
  )
}
