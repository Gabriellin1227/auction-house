import { useState, type FormEvent } from 'react'
import { register, signIn } from '../api/auction'
import type { User } from '../types'

export default function AuthForm({
  mode,
  onSuccess,
}: {
  mode: 'login' | 'register'
  onSuccess: (user: User) => void
}) {
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const credentials = {
      email: String(data.get('email')),
      password: String(data.get('password')),
    }
    setPending(true)
    setError('')
    try {
      const result =
        mode === 'login'
          ? await signIn(credentials)
          : await register({
              ...credentials,
              name: String(data.get('name')),
              role: data.get('role') === 'auctioneer' ? 'auctioneer' : 'bidder',
            })
      onSuccess(result.user)
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : 'Não foi possível conectar à API.',
      )
    } finally {
      setPending(false)
    }
  }
  return (
    <form className="auth-form" onSubmit={submit} aria-busy={pending}>
      {mode === 'register' && (
        <label>
          Nome
          <input name="name" autoComplete="name" maxLength={150} required />
        </label>
      )}
      <label>
        E-mail
        <input name="email" type="email" autoComplete="email" required />
      </label>
      <label>
        Senha
        <input
          name="password"
          type="password"
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          minLength={mode === 'register' ? 8 : 1}
          maxLength={128}
          required
        />
      </label>
      {mode === 'register' && (
        <label>
          Tipo de Conta
          <select name="role">
            <option value="bidder">Licitante</option>
            <option value="auctioneer">Leiloeiro(a)</option>
          </select>
        </label>
      )}
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
      <button className="btn btn--gold" disabled={pending}>
        {pending ? 'Aguarde…' : mode === 'login' ? 'Entrar' : 'Criar conta'}
      </button>
    </form>
  )
}
