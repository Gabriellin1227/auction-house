import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { http } from '../api/client'
import { useAsync } from '../hooks/useAsync'
import { formatMoney } from '../utils/format'

interface Audit {
  integrity: 'valid' | 'invalid' | 'unavailable'
  checkpoint_status: 'anchored' | 'pending' | 'invalid' | 'unavailable'
  verified_count: number
  checkpoint_sequence: number | null
  head_sequence: number | null
  issues: string[]
  next_after: number | null
  history: {
    id: string
    sequence: number
    bidder_public_id: string
    amount_cents: number
    accepted_at: string
    previous_hash: string
    record_hash: string
    signature: string
  }[]
}

function AuditContent({ id }: { id: string }) {
  const [revision, setRevision] = useState(0)
  const [after, setAfter] = useState(0)
  const { data, loading, error } = useAsync(
    () => http.get<Audit>(`/lots/${id}/audit?after=${after}`),
    [id, revision, after],
  )
  return (
    <article className="container section audit-page">
      <span className="eyebrow">Transparência</span>
      <h1>Auditoria pública do lote</h1>
      <p>
        Consulta sem login. Identificadores públicos preservam nome, e-mail e
        saldo dos licitantes.
      </p>
      <button
        className="btn btn--gold"
        disabled={loading}
        onClick={() => setRevision((value) => value + 1)}
      >
        Verificar novamente
      </button>
      {loading && (
        <p role="status">Verificando cadeia, assinaturas e checkpoints…</p>
      )}
      {error && <p role="alert">{error.message}</p>}
      {!loading && !error && data && (
        <>
          <h2 className={data.integrity === 'invalid' ? 'audit-invalid' : ''}>
            {data.integrity === 'invalid'
              ? 'Inconsistência detectada'
              : data.integrity === 'unavailable'
                ? 'Verificação indisponível'
                : data.checkpoint_status === 'anchored'
                  ? 'Histórico íntegro e ancorado'
                  : 'Cadeia válida · checkpoint pendente'}
          </h2>
          <p>
            {data.verified_count} lances examinados · Cabeçalho:{' '}
            {data.head_sequence ?? 'ausente'} · Checkpoint:{' '}
            {data.checkpoint_sequence ?? 'ainda não gravado'}
          </p>
          <ul>
            {data.issues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
          {data.checkpoint_status === 'pending' && (
            <p>
              O worker ainda precisa ancorar o estado atual. Até lá, esta
              consulta não comprova proteção contra restauração de versões
              anteriores do trecho pendente.
            </p>
          )}
          <h2>Histórico verificado nesta consulta</h2>
          {data.history.length === 0 && <p>Nenhum lance nesta página.</p>}
          <ol className="bid-history">
            {data.history.map((bid) => (
              <li key={bid.id}>
                <strong>
                  #{bid.sequence} · {formatMoney(bid.amount_cents)}
                </strong>
                <span>Licitante {bid.bidder_public_id}</span>
                <time dateTime={bid.accepted_at}>
                  {new Date(bid.accepted_at).toLocaleString('pt-BR')}
                </time>
                <details>
                  <summary>Hashes e assinatura</summary>
                  <p>
                    Anterior: <code>{bid.previous_hash}</code>
                  </p>
                  <p>
                    Registro: <code>{bid.record_hash}</code>
                  </p>
                  <p>
                    HMAC: <code>{bid.signature}</code>
                  </p>
                </details>
              </li>
            ))}
          </ol>
          {after > 0 && (
            <button className="btn btn--ghost" onClick={() => setAfter(0)}>
              Início do histórico
            </button>
          )}
          {data.next_after !== null && (
            <button
              className="btn btn--ghost"
              onClick={() => setAfter(data.next_after!)}
            >
              Próximos lances
            </button>
          )}
          <p>
            A verificação examina a cadeia completa em cada consulta. A
            paginação limita apenas os registros exibidos.
          </p>
          <p>
            Assinaturas usam uma chave privada do servidor. Esta proteção não
            cobre comprometimento da chave nem um administrador capaz de
            reescrever simultaneamente banco e journal. A remoção de todo o
            journal aparece como checkpoint pendente; não comprova histórico
            ancorado.
          </p>
        </>
      )}
      <p>
        <Link className="back-link" to={`/lots/${id}`}>
          Consultar lote
        </Link>
      </p>
    </article>
  )
}

export default function AuditPage() {
  const { lotId = '' } = useParams()
  return <AuditContent key={lotId} id={lotId} />
}
