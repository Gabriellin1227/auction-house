import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

interface HeaderProps {
  query: string
  onQuery: (q: string) => void
  onSignIn: () => void
  onRegister: () => void
  userName?: string
  onSignOut: () => void
}

export default function Header({
  query,
  onQuery,
  onSignIn,
  onRegister,
  userName,
  onSignOut,
}: HeaderProps) {
  const [value, setValue] = useState(query)
  useEffect(() => setValue(query), [query])

  const submit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    onQuery(value.trim())
  }

  return (
    <header className="header">
      <div className="container header__row">
        <Link className="logo" to="/" onClick={() => setValue('')}>
          <span className="logo__gold">The Yorknew</span> Leilão Online
        </Link>

        <form className="search" onSubmit={submit} role="search">
          <svg
            className="search__icon"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3.5-3.5" />
          </svg>
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Buscar lotes, origens e categorias..."
            aria-label="Buscar"
          />
        </form>

        <div className="header__actions">
          {userName ? (
            <>
              <Link className="account-name" to="/account">
                Minha conta · {userName}
              </Link>
              <button className="link-btn" onClick={onSignOut}>
                Sair
              </button>
            </>
          ) : (
            <>
              <button className="link-btn" onClick={onSignIn}>
                Entrar
              </button>
              <button className="btn btn--gold" onClick={onRegister}>
                Criar conta
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
