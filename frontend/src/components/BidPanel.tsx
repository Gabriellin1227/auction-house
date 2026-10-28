import { useRef, useState, type FormEvent } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import type { CatalogueNavigation } from '../App'
import { USE_MOCK } from '../api/auction'
import { ApiError, http } from '../api/client'
import { useAsync } from '../hooks/useAsync'
import { formatMoney } from '../utils/format'
import type { BidAccepted, BidRecord, Lot } from '../types'

export function BidHistory({ lot }: { lot: Lot }) {
  const [after, setAfter] = useState(0)
  const { data, loading, error } = useAsync(
    () =>
      USE_MOCK
        ? Promise.resolve([] as BidRecord[])
        : http.get<BidRecord[]>(`/lots/${lot.id}/bids?after=${after}`),
    [lot.id, lot.version, after],
  )
  if (USE_MOCK) return <p>Histórico indisponível na prévia ilustrativa.</p>
  return (
    <div>
      {loading && <p role="status">Carregando lances…</p>}
      {error && <p role="alert">{error.message}</p>}
      {!loading && !error && data?.length === 0 && (
        <p>Ainda não há lances registrados nesta página.</p>
      )}
      <ol className="bid-history" aria-label="Lances aceitos">
        {data?.map((bid) => (
          <li key={bid.id}>
            <strong>
              #{bid.sequence} · {formatMoney(bid.amount_cents)}
            </strong>
            <span title={bid.bidder_public_id}>
              Licitante {bid.bidder_public_id}
            </span>
            <time dateTime={bid.accepted_at}>
              {new Date(bid.accepted_at).toLocaleString('pt-BR')}
            </time>
          </li>
        ))}
      </ol>
      {after > 0 && (
        <button className="btn btn--ghost" onClick={() => setAfter(0)}>
          Voltar ao início do histórico
        </button>
      )}
      {data?.length === 100 && (
        <button
          className="btn btn--ghost"
          onClick={() => setAfter(data[data.length - 1].sequence)}
        >
          Próximos lances
        </button>
      )}
    </div>
  )
}

export default function BidPanel({
  lot,
  closed,
  onAccepted,
}: {
  lot: Lot
  closed: boolean
  onAccepted: (bid: BidAccepted) => void
}) {
  const { user, requestLogin } = useOutletContext<CatalogueNavigation>()
  const [pending, setPending] = useState(false)
  const submitting = useRef(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const wasLeading = useRef<string | null>(null)
  const minimum = lot.currentBid + (lot.bids > 0 ? lot.increment || 0 : 0)
  const leading = !!user && lot.leaderPublicId === user.public_id
  if (leading) wasLeading.current = user.public_id
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting.current) return
    const amount = Number(new FormData(event.currentTarget).get('amount'))
    const cents = Math.round(amount * 100)
    if (!Number.isSafeInteger(cents) || cents < minimum) {
      setError(`O lance mínimo é ${formatMoney(minimum)}.`)
      return
    }
    submitting.current = true
    setPending(true)
    setError('')
    setMessage('')
    try {
      const bid = await http.post<BidAccepted>(`/lots/${lot.id}/bids`, {
        amount_cents: cents,
      })
      onAccepted(bid)
      setMessage(
        bid.extended
          ? 'Lance aceito! Prazo prorrogado para dois minutos após o aceite.'
          : 'Lance aceito! Seu saldo está reservado.',
      )
    } catch (caught) {
      const failure = caught as Error
      setError(
        caught instanceof ApiError && caught.status === 0
          ? `${failure.message} O resultado pode ter sido registrado. Atualize o lote e consulte sua carteira antes de tentar novamente.`
          : failure.message,
      )
    } finally {
      submitting.current = false
      setPending(false)
    }
  }
  if (USE_MOCK)
    return (
      <p className="lot-details__notice">
        Prévia ilustrativa: lances desativados.
      </p>
    )
  return (
    <section aria-label="Oferecer lance">
      <p className="lot-details__notice">
        {leading
          ? lot.closureComplete && lot.sold
            ? 'Você arrematou este lote.'
            : closed
              ? 'Você liderou o lote. Consulte o resultado do fechamento abaixo.'
              : 'Você está ganhando este lote.'
          : wasLeading.current === user?.public_id && user?.role === 'bidder'
            ? 'Você foi superado. Sua reserva deste lote foi liberada.'
            : lot.leaderPublicId && user?.role === 'bidder'
              ? 'Outro licitante está na liderança.'
              : 'O valor do líder fica reservado na carteira.'}
      </p>
      {closed || lot.status === 'closed' || lot.status === 'cancelled' ? (
        <p>
          {lot.closureComplete
            ? lot.sold
              ? 'Leilão encerrado e liquidado.'
              : 'Leilão encerrado sem vencedor.'
            : 'Prazo encerrado. Aguardando o fechamento automático.'}
          {lot.receiptId && (
            <>
              {' '}
              <Link className="back-link" to={`/receipts/${lot.receiptId}`}>
                Ver comprovante público
              </Link>
            </>
          )}
        </p>
      ) : lot.status === 'scheduled' ? (
        <p>
          O lote ainda não começou. Início:{' '}
          {new Date(lot.startsAt!).toLocaleString('pt-BR')}.
        </p>
      ) : !user ? (
        <button className="btn btn--gold" onClick={requestLogin}>
          Entrar para dar lance
        </button>
      ) : user.role !== 'bidder' ? (
        <p>Leiloeiros não podem dar lances.</p>
      ) : leading ? null : (
        <form className="bid-form" onSubmit={submit}>
          <label>
            Seu lance (R$)
            <input
              key={minimum}
              name="amount"
              type="number"
              min={minimum / 100}
              step="0.01"
              defaultValue={(minimum / 100).toFixed(2)}
              required
              disabled={pending}
            />
          </label>
          <small>Mínimo: {formatMoney(minimum)}</small>
          <button className="btn btn--gold" disabled={pending}>
            {pending ? 'Enviando lance…' : 'Confirmar lance'}
          </button>
        </form>
      )}
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
      {user?.role === 'bidder' && (
        <Link className="back-link" to="/account">
          Consultar saldo e extrato
        </Link>
      )}
      <p className="lot-details__notice">
        A sala recebe atualizações automáticas. Use Atualizar lote se precisar
        conferir a disputa durante uma falha de conexão.
      </p>
    </section>
  )
}
