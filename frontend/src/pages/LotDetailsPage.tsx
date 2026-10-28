import { Link, useLocation, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { fetchLot, USE_MOCK } from '../api/auction'
import { useAsync } from '../hooks/useAsync'
import { useCountdown } from '../hooks/useCountdown'
import { formatMoney } from '../utils/format'
import type { Lot } from '../types'

function LotInformation({ lot }: { lot: Lot }) {
  const { label, closed } = useCountdown(lot.endsAt)
  return (
    <>
      <div className="lot-details__grid">
        <figure className="lot-details__gallery">
          <img
            src={lot.image}
            alt={lot.title}
            onError={(event) => {
              if (!event.currentTarget.src.endsWith('/images/placeholder.svg'))
                event.currentTarget.src = '/images/placeholder.svg'
            }}
          />
          <figcaption>
            Lote {lot.number} · {lot.categoryName}
          </figcaption>
        </figure>
        <section className="lot-details__summary" aria-labelledby="lot-title">
          <div className="lot-details__meta">
            <span className="eyebrow">Lote {lot.number}</span>
            <span className="lot-status">
              {USE_MOCK ? 'Prévia' : closed ? 'Encerrado' : 'Catálogo'}
            </span>
          </div>
          <h1 id="lot-title">{lot.title}</h1>
          <p className="lot-details__category">{lot.categoryName}</p>
          <div className="lot-details__price">
            <span>Lance atual</span>
            <strong>{formatMoney(lot.currentBid)}</strong>
            <small>
              {lot.bids}{' '}
              {lot.bids === 1 ? 'lance registrado' : 'lances registrados'}
            </small>
          </div>
          <div className="lot-details__countdown">
            <span>{closed ? 'Prazo encerrado' : 'Tempo restante'}</span>
            <strong>{label}</strong>
          </div>
          <button className="btn btn--gold lot-details__bid" disabled>
            Lances indisponíveis nesta prévia
          </button>
          <p className="lot-details__notice">
            {USE_MOCK
              ? 'Este item faz parte do catálogo ilustrativo. Nenhum lance ou cobrança será realizado.'
              : 'O envio de lances ainda não está disponível.'}
          </p>
        </section>
      </div>
      <div className="lot-details__information">
        <section aria-labelledby="item-information">
          <span className="eyebrow">O objeto</span>
          <h2 id="item-information">Informações do lote</h2>
          <dl>
            <div>
              <dt>Identificação</dt>
              <dd>Lote {lot.number}</dd>
            </div>
            <div>
              <dt>Categoria</dt>
              <dd>{lot.categoryName}</dd>
            </div>
            <div>
              <dt>Encerramento</dt>
              <dd>
                <time dateTime={new Date(lot.endsAt).toISOString()}>
                  {new Date(lot.endsAt).toLocaleString('pt-BR')}
                </time>
              </dd>
            </div>
          </dl>
        </section>
        <section aria-labelledby="bid-history">
          <span className="eyebrow">A disputa</span>
          <h2 id="bid-history">Histórico de lances</h2>
          <p className="lot-details__empty">
            {lot.bids === 0
              ? 'Ainda não há lances registrados para este lote.'
              : 'O histórico detalhado será disponibilizado com a integração dos leilões.'}
          </p>
        </section>
      </div>
    </>
  )
}

function Details({ id }: { id: string }) {
  const { search } = useLocation()
  const { data: lot, loading, error } = useAsync(() => fetchLot(id), [id])
  const back = `/${search}`
  return (
    <article className="container lot-details">
      <nav className="breadcrumbs" aria-label="Caminho de navegação">
        <Link to={back}>Vitrine</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">
          {lot ? `Lote ${lot.number}` : 'Detalhes do lote'}
        </span>
      </nav>
      {loading ? (
        <div role="status" className="lot-details__loading">
          Abrindo o cofre…
        </div>
      ) : error ? (
        <section className="lot-details__error" role="alert">
          <h1>
            {error instanceof ApiError && error.status === 404
              ? 'Lote não encontrado'
              : 'Não foi possível carregar o lote'}
          </h1>
          <p>{error.message}</p>
          <Link className="back-link" to={back}>
            Voltar à vitrine
          </Link>
        </section>
      ) : lot ? (
        <LotInformation lot={lot} />
      ) : null}
    </article>
  )
}

export default function LotDetailsPage() {
  const { lotId = '' } = useParams()
  return <Details key={lotId} id={lotId} />
}
