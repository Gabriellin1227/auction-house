import { useRef, useState, type FormEvent } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import type { CatalogueNavigation } from '../App'
import { http } from '../api/client'
import { signOut } from '../api/auction'
import { useAsync } from '../hooks/useAsync'
import { formatMoney } from '../utils/format'
import type { Lot, User } from '../types'
import Dialog from '../components/Dialog'
import Participations from '../components/Participations'

type Wallet = {
  balance_cents: number
  reserved_cents: number
  available_cents: number
}
type Entry = {
  id: string
  type: string
  amount_cents: number
  created_at: string
}
type Item = { id: number; title: string; image: string }
const entryNames: Record<string, string> = {
  deposit: 'Depósito simulado',
  reserve: 'Reserva',
  release: 'Liberação',
  debit: 'Débito',
  credit: 'Crédito',
}

function SellerPanel() {
  const [revision, setRevision] = useState(0)
  const { data: lots, error } = useAsync(
    () => http.get<Lot[]>('/lots/mine'),
    [revision],
  )
  const { data: summary, error: summaryError } = useAsync(
    () =>
      http.get<{ total_lots: number; total_received_cents: number }>(
        '/auctioneers/me/summary',
      ),
    [revision],
  )
  const [items, setItems] = useState<Item[]>([])
  const [selected, setSelected] = useState<Item | null>(null)
  const [editing, setEditing] = useState<Lot | null>(null)
  const [cancel, setCancel] = useState<Lot | null>(null)
  const [message, setMessage] = useState('')
  const [pending, setPending] = useState(false)
  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setPending(true)
    setMessage('')
    try {
      setItems(
        await http.get<Item[]>(
          `/catalog/items?q=${encodeURIComponent(String(form.get('q')))}`,
        ),
      )
    } catch (error) {
      setMessage((error as Error).message)
    } finally {
      setPending(false)
    }
  }
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setPending(true)
    setMessage('')
    const values = {
      category: String(form.get('category')),
      opening_bid_cents: Math.round(Number(form.get('price')) * 100),
      min_increment_cents: Math.round(Number(form.get('increment')) * 100),
      starts_at: new Date(String(form.get('start'))).toISOString(),
      ends_at: new Date(String(form.get('end'))).toISOString(),
    }
    try {
      if (editing) await http.patch(`/lots/${editing.id}`, values)
      else
        await http.post('/lots', { ...values, external_item_id: selected!.id })
      setSelected(null)
      setEditing(null)
      setRevision((value) => value + 1)
      setMessage('Lote salvo com sucesso.')
    } catch (error) {
      setMessage((error as Error).message)
    } finally {
      setPending(false)
    }
  }
  const localDate = (ms?: number) =>
    ms
      ? new Date(ms - new Date(ms).getTimezoneOffset() * 60000)
          .toISOString()
          .slice(0, 16)
      : ''
  return (
    <section className="account-section">
      <h2>Meus lotes</h2>
      {summary && (
        <p>
          Total recebido:{' '}
          <strong>{formatMoney(summary.total_received_cents)}</strong> ·{' '}
          {summary.total_lots} lotes
        </p>
      )}
      {summaryError && <p role="alert">{summaryError.message}</p>}
      <button
        className="btn btn--ghost"
        onClick={() => setRevision((value) => value + 1)}
      >
        Atualizar resultados
      </button>
      {error && <p role="alert">{error.message}</p>}
      <form className="account-inline" onSubmit={search}>
        <label>
          Buscar item no acervo público
          <input
            name="q"
            placeholder="Artista, título ou objeto"
            maxLength={120}
          />
        </label>
        <button className="btn btn--gold" disabled={pending}>
          Buscar no acervo
        </button>
      </form>
      <div className="import-grid">
        {items.map((item) => (
          <button
            key={item.id}
            className="import-card"
            onClick={() => {
              setSelected(item)
              setEditing(null)
            }}
          >
            <img src={item.image} alt="" />
            <span>{item.title}</span>
            <small>Selecionar item</small>
          </button>
        ))}
      </div>
      {(selected || editing) && (
        <form
          className="auth-form account-editor"
          key={String(selected?.id || editing?.id)}
          onSubmit={save}
        >
          <h3>
            {editing ? 'Editar lote agendado' : 'Criar lote'} ·{' '}
            {selected?.title || editing?.title}
          </h3>
          <label>
            Categoria
            <select
              name="category"
              defaultValue={editing?.category || 'fine-art'}
            >
              <option value="fine-art">Belas-artes</option>
              <option value="jewelry">Joias</option>
              <option value="ceramics">Cerâmica</option>
              <option value="furniture">Mobília</option>
              <option value="horology">Relojoaria</option>
              <option value="coins-manuscripts">Moedas e manuscritos</option>
              <option value="curiosities">Curiosidades</option>
            </select>
          </label>
          <label>
            Lance inicial (R$)
            <input
              name="price"
              type="number"
              min="0.01"
              max="10000000000"
              step="0.01"
              defaultValue={editing ? editing.currentBid / 100 : ''}
              required
            />
          </label>
          <label>
            Incremento mínimo (R$)
            <input
              name="increment"
              type="number"
              min="0.01"
              step="0.01"
              defaultValue={editing ? (editing.increment || 0) / 100 : ''}
              required
            />
          </label>
          <label>
            Início
            <input
              name="start"
              type="datetime-local"
              defaultValue={localDate(editing?.startsAt)}
              required
            />
          </label>
          <label>
            Fim
            <input
              name="end"
              type="datetime-local"
              defaultValue={localDate(editing?.endsAt)}
              required
            />
          </label>
          <button className="btn btn--gold" disabled={pending}>
            Salvar lote
          </button>
          <button
            type="button"
            onClick={() => {
              setSelected(null)
              setEditing(null)
            }}
          >
            Descartar edição
          </button>
        </form>
      )}
      {message && <p role="status">{message}</p>}
      <div className="account-list">
        {lots?.length === 0 && <p>Você ainda não publicou lotes.</p>}
        {lots?.map((lot) => (
          <article key={lot.id}>
            <Link to={`/lots/${lot.id}`}>{lot.title}</Link>
            <p>
              {
                (
                  {
                    live: 'Ao vivo',
                    scheduled: 'Agendado',
                    closed: 'Encerrado',
                    cancelled: 'Cancelado',
                  } as Record<string, string>
                )[lot.status || 'scheduled']
              }{' '}
              · {formatMoney(lot.currentBid)}
            </p>
            {lot.status === 'closed' && (
              <p>
                {lot.closureComplete
                  ? lot.sold
                    ? `Arrematado por ${formatMoney(lot.settledAmount || 0)}`
                    : 'Encerrado sem vencedor'
                  : 'Aguardando liquidação automática'}
              </p>
            )}
            {lot.receiptId && (
              <Link className="back-link" to={`/receipts/${lot.receiptId}`}>
                Ver comprovante público
              </Link>
            )}
            <div className="account-inline">
              <button
                disabled={pending || lot.status !== 'scheduled' || lot.bids > 0}
                onClick={() => {
                  setEditing(lot)
                  setSelected(null)
                }}
              >
                Editar
              </button>
              <button
                disabled={
                  pending ||
                  lot.bids > 0 ||
                  lot.status === 'closed' ||
                  lot.status === 'cancelled'
                }
                title={
                  lot.bids > 0
                    ? 'Lote com lances não pode ser cancelado'
                    : 'Cancelar lote'
                }
                onClick={() => setCancel(lot)}
              >
                Cancelar lote
              </button>
            </div>
          </article>
        ))}
      </div>
      {cancel && (
        <Dialog title="Cancelar lote?" onClose={() => setCancel(null)}>
          <p>O lote será retirado da vitrine. Seu histórico será preservado.</p>
          <button
            className="btn btn--gold"
            disabled={pending}
            onClick={async () => {
              setPending(true)
              try {
                await http.delete(`/lots/${cancel.id}`)
                setRevision((value) => value + 1)
                setCancel(null)
                setMessage('Lote cancelado.')
              } catch (error) {
                setMessage((error as Error).message)
                setCancel(null)
              } finally {
                setPending(false)
              }
            }}
          >
            Confirmar cancelamento
          </button>
        </Dialog>
      )}
    </section>
  )
}

export default function AccountPage() {
  const { user, setUser, requestLogin } =
    useOutletContext<CatalogueNavigation>()
  const [revision, setRevision] = useState(0)
  const { data, error } = useAsync(
    async () =>
      user
        ? Promise.all([
            http.get<Wallet>('/wallets/me'),
            http.get<Entry[]>('/wallets/me/entries'),
          ])
        : null,
    [user?.id, revision],
  )
  const [message, setMessage] = useState('')
  const [pending, setPending] = useState(false)
  const [deactivate, setDeactivate] = useState(false)
  const depositKey = useRef<string | null>(null)
  if (!user)
    return (
      <section className="container section">
        <h1>Minha conta</h1>
        <p>Entre para acessar seu perfil, carteira e lotes.</p>
        <button className="btn btn--gold" onClick={requestLogin}>
          Entrar
        </button>
      </section>
    )
  async function update(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setPending(true)
    try {
      setUser(
        await http.patch<User>('/users/me', {
          name: form.get('name'),
          email: form.get('email'),
        }),
      )
      setMessage('Perfil atualizado.')
    } catch (error) {
      setMessage((error as Error).message)
    } finally {
      setPending(false)
    }
  }
  async function deposit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setPending(true)
    depositKey.current ||= crypto.randomUUID()
    try {
      await http.post(
        '/wallets/me/deposits',
        { amount_cents: Math.round(Number(form.get('amount')) * 100) },
        { 'Idempotency-Key': depositKey.current },
      )
      depositKey.current = null
      setRevision((value) => value + 1)
      setMessage('Depósito simulado registrado.')
    } catch (error) {
      setMessage((error as Error).message)
    } finally {
      setPending(false)
    }
  }
  return (
    <div className="container account-page">
      <h1>Minha conta</h1>
      <button
        className="btn btn--ghost"
        onClick={() => setRevision((value) => value + 1)}
      >
        Atualizar carteira e participações
      </button>
      <p>
        {user.role === 'auctioneer' ? 'Leiloeiro' : 'Licitante'} · {user.name}
      </p>
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error.message}</p>}
      <section className="account-section">
        <h2>Meu perfil</h2>
        <form className="auth-form" onSubmit={update}>
          <label>
            Nome
            <input
              name="name"
              defaultValue={user.name}
              maxLength={150}
              required
            />
          </label>
          <label>
            E-mail
            <input
              name="email"
              type="email"
              defaultValue={user.email}
              required
            />
          </label>
          <button className="btn btn--gold" disabled={pending}>
            Salvar perfil
          </button>
        </form>
      </section>
      <section className="account-section">
        <h2>Minha carteira</h2>
        <div className="wallet-summary">
          {[
            ['Total', data?.[0].balance_cents],
            ['Comprometido', data?.[0].reserved_cents],
            ['Disponível', data?.[0].available_cents],
          ].map(([label, value]) => (
            <div key={label}>
              <span>{label}</span>
              <strong>
                {typeof value === 'number' ? formatMoney(value) : '…'}
              </strong>
            </div>
          ))}
        </div>
        <p>
          O saldo comprometido corresponde às reservas dos lotes em que você
          lidera.
        </p>
        {user.role === 'bidder' && (
          <form className="account-inline" onSubmit={deposit}>
            <label>
              Depósito simulado (R$)
              <input
                name="amount"
                type="number"
                min="0.01"
                max="1000000"
                step="0.01"
                onChange={() => {
                  depositKey.current = null
                }}
                required
              />
            </label>
            <button className="btn btn--gold" disabled={pending}>
              Depositar
            </button>
          </form>
        )}
        <h3>Extrato</h3>
        {data?.[1].length === 0 && <p>Ainda não há movimentações.</p>}
        <ul className="account-list">
          {data?.[1].map((entry) => (
            <li key={entry.id}>
              {entryNames[entry.type] || 'Movimentação'} ·{' '}
              {formatMoney(entry.amount_cents)} ·{' '}
              {new Date(entry.created_at).toLocaleString('pt-BR')}
            </li>
          ))}
        </ul>
      </section>
      {user.role === 'auctioneer' && <SellerPanel />}
      {user.role === 'bidder' && (
        <Participations key={user.id} revision={revision} />
      )}
      <section className="account-section">
        <h2>Inativar conta</h2>
        <p>
          Seus dados de transações serão preservados. A conta deixará de acessar
          o sistema.
        </p>
        <button className="btn" onClick={() => setDeactivate(true)}>
          Inativar minha conta
        </button>
      </section>
      {deactivate && (
        <Dialog
          title="Inativar sua conta?"
          onClose={() => setDeactivate(false)}
        >
          <p>
            Seu acesso será encerrado. Esta ação não apaga histórico nem
            movimentações.
          </p>
          <button
            className="btn btn--gold"
            disabled={pending}
            onClick={async () => {
              setPending(true)
              try {
                await http.delete('/users/me')
                signOut()
                setUser(null)
                setDeactivate(false)
              } catch (error) {
                setMessage((error as Error).message)
                setDeactivate(false)
              } finally {
                setPending(false)
              }
            }}
          >
            Confirmar inativação
          </button>
        </Dialog>
      )}
    </div>
  )
}
