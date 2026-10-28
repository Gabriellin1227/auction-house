import { useState } from 'react'
import { Link } from 'react-router-dom'
import { http } from '../api/client'
import { useAsync } from '../hooks/useAsync'
import { formatMoney } from '../utils/format'
import type { Lot } from '../types'

interface Participation {
  lot: Lot
  highest_bid_cents: number
  leading: boolean
  won: boolean
  receipt_id: string | null
}

export default function Participations({ revision }: { revision: number }) {
  const [offset, setOffset] = useState(0)
  const { data, loading, error } = useAsync(
    () =>
      http.get<Participation[]>(`/bidders/me/participations?offset=${offset}`),
    [revision, offset],
  )
  return (
    <section className="account-section">
      <h2>Minhas participações e arremates</h2>
      {loading && <p role="status">Consultando participações…</p>}
      {error && <p role="alert">{error.message}</p>}
      {data?.length === 0 && <p>Nenhuma participação nesta página.</p>}
      <ul className="account-list">
        {data?.map((item) => (
          <li key={item.lot.id}>
            <Link to={`/lots/${item.lot.id}`}>{item.lot.title}</Link>
            <p>Meu maior lance: {formatMoney(item.highest_bid_cents)}</p>
            <p>
              {item.won
                ? 'Arrematado por você'
                : item.lot.closureComplete
                  ? 'Encerrado sem arremate para você'
                  : item.lot.status === 'closed'
                    ? 'Prazo encerrado · aguardando liquidação'
                    : item.leading
                      ? 'Você está ganhando'
                      : 'Você foi superado'}
            </p>
            {item.receipt_id && (
              <Link className="back-link" to={`/receipts/${item.receipt_id}`}>
                Ver comprovante público
              </Link>
            )}
          </li>
        ))}
      </ul>
      {offset > 0 && (
        <button
          className="btn btn--ghost"
          onClick={() => setOffset(Math.max(0, offset - 100))}
        >
          Página anterior
        </button>
      )}
      {data?.length === 100 && (
        <button
          className="btn btn--ghost"
          onClick={() => setOffset(offset + 100)}
        >
          Próximas participações
        </button>
      )}
    </section>
  )
}
