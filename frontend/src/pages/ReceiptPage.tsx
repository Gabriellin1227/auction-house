import { mediaUrl } from '../api/client'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { http } from '../api/client'
import { useAsync } from '../hooks/useAsync'
import { formatMoney } from '../utils/format'

interface Receipt {
  id: string
  lot_id: string
  item_title: string
  image: string
  source_url: string
  winner_public_id: string
  amount_cents: number
  currency: string
  settled_at: string
}

function ReceiptContent({ id }: { id: string }) {
  const { data, loading, error } = useAsync(
    () => http.get<Receipt>(`/receipts/${id}`),
    [id],
  )
  const [message, setMessage] = useState('')
  return (
    <article className="container section receipt-page">
      <h1>Comprovante de arremate</h1>
      {loading && <p role="status">Carregando comprovante…</p>}
      {error && <p role="alert">{error.message}</p>}
      {data && (
        <>
          <p>Arremate com saldo simulado · BRL</p>
          <img
            src={mediaUrl(data.image)}
            alt={data.item_title}
            className="receipt-image"
          />
          <h2>{data.item_title}</h2>
          <dl className="receipt-data">
            <dt>Valor do arremate</dt>
            <dd>{formatMoney(data.amount_cents)}</dd>
            <dt>Licitante vencedor (identificador público)</dt>
            <dd>{data.winner_public_id}</dd>
            <dt>Liquidação</dt>
            <dd>{new Date(data.settled_at).toLocaleString('pt-BR')}</dd>
            <dt>Comprovante</dt>
            <dd>{data.id}</dd>
          </dl>
          <label className="receipt-link">
            Link público para compartilhar
            <input
              readOnly
              value={window.location.href}
              onFocus={(event) => event.currentTarget.select()}
            />
          </label>
          <button
            className="btn btn--gold"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(window.location.href)
                setMessage('Link copiado.')
              } catch {
                setMessage('Selecione e copie o link no campo acima.')
              }
            }}
          >
            Copiar link
          </button>
          {message && <p role="status">{message}</p>}
          <p>
            <Link className="back-link" to={`/lots/${data.lot_id}`}>
              Consultar lote
            </Link>
          </p>
          <p>
            <Link className="back-link" to={`/lots/${data.lot_id}/audit`}>
              Auditar histórico público
            </Link>
          </p>
          <p>
            Este comprovante registra uma operação de demonstração. Não é nota
            fiscal.
          </p>
        </>
      )}
    </article>
  )
}

export default function ReceiptPage() {
  const { receiptId = '' } = useParams()
  return <ReceiptContent key={receiptId} id={receiptId} />
}
