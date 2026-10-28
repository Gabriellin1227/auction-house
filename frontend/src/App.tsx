import { useEffect, useState } from 'react'
import {
  BrowserRouter,
  Link,
  Outlet,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useSearchParams,
} from 'react-router-dom'
import Header from './components/Header'
import CategoryNav from './components/CategoryNav'
import { USE_MOCK, signOut } from './api/auction'
import Dialog from './components/Dialog'
import AuthForm from './components/AuthForm'
import CataloguePage from './pages/CataloguePage'
import LotDetailsPage from './pages/LotDetailsPage'
import AccountPage from './pages/AccountPage'
import ReceiptPage from './pages/ReceiptPage'
import AuditPage from './pages/AuditPage'
import type { User } from './types'

export interface CatalogueNavigation {
  user: User | null
  setUser: (user: User | null) => void
  requestLogin: () => void
  selectCategory: (slug: string) => void
}

function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [params] = useSearchParams()
  const category = params.get('category') || ''
  const query = params.get('q') || ''
  const [user, setUser] = useState<User | null>(null)
  const [dialog, setDialog] = useState<'login' | 'register' | null>(null)

  const catalogue = (key: string, value: string) => {
    const search = new URLSearchParams()
    if (value) search.set(key, value)
    navigate({ pathname: '/', search: search.toString() })
  }
  const selectCategory = (slug: string) => catalogue('category', slug)

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [location.pathname, location.search])

  return (
    <>
      <a className="skip-link" href="#page-content">
        Ir para o conteúdo
      </a>
      <div className="app-topbar">
        <Header
          query={query}
          onQuery={(value) => catalogue('q', value)}
          onSignIn={() => setDialog('login')}
          onRegister={() => setDialog('register')}
          userName={user?.name}
          onSignOut={() => {
            signOut()
            setUser(null)
          }}
        />
        <CategoryNav active={category} onSelect={selectCategory} />
      </div>
      <main id="page-content" tabIndex={-1}>
        {USE_MOCK && (
          <p className="preview-note container">
            Prévia do catálogo · Lotes ilustrativos.
          </p>
        )}
        <Outlet
          context={
            {
              selectCategory,
              user,
              setUser,
              requestLogin: () => setDialog('login'),
            } satisfies CatalogueNavigation
          }
        />
      </main>
      {(dialog === 'login' || dialog === 'register') && (
        <Dialog
          title={dialog === 'login' ? 'Entrar' : 'Criar conta'}
          onClose={() => setDialog(null)}
        >
          <AuthForm
            mode={dialog}
            onSuccess={(account) => {
              setUser(account)
              setDialog(null)
            }}
          />
        </Dialog>
      )}
      <footer className="footer">
        <div className="container">© The Yorknew Leilão Online.</div>
      </footer>
    </>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<CataloguePage />} />
          <Route path="lots/:lotId" element={<LotDetailsPage />} />
          <Route path="lots/:lotId/audit" element={<AuditPage />} />
          <Route path="account" element={<AccountPage />} />
          <Route path="receipts/:receiptId" element={<ReceiptPage />} />
          <Route
            path="*"
            element={
              <section className="container section">
                <h1>Página não encontrada</h1>
                <Link className="back-link" to="/">
                  Voltar à vitrine
                </Link>
              </section>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
