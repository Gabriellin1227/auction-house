import { useState } from 'react'
import Header from './components/Header'
import CategoryNav from './components/CategoryNav'
import SubscribeBar from './components/SubscribeBar'
import CategoryGrid from './components/CategoryGrid'
import StatsBar from './components/StatsBar'
import LotGrid from './components/LotGrid'
import { USE_MOCK, signOut } from './api/auction'
import Dialog from './components/Dialog'
import AuthForm from './components/AuthForm'
import { formatMoney } from './utils/format'
import type { User, Lot } from './types'

export default function App() {
  const [category, setCategory] = useState<string>('') // "" = todos
  const [query, setQuery] = useState<string>('')

  const filtering = category !== '' || query !== ''

  const selectCategory = (slug: string) => {
    setCategory(slug)
    setQuery('')
  }

  const [user, setUser] = useState<User | null>(null)
  const [dialog, setDialog] = useState<'login' | 'register' | 'help' | null>(
    null,
  )
  const [lot, setLot] = useState<Lot | null>(null)
  const openLot = (item: Lot) => setLot(item)
  const signIn = () => setDialog('login')
  const register = () => setDialog('register')
  const howItWorks = () => setDialog('help')

  return (
    <>
      <Header
        query={query}
        onQuery={(q) => {
          setQuery(q)
          setCategory('')
        }}
        onSignIn={signIn}
        onRegister={register}
        userName={user?.name}
        onSignOut={() => {
          signOut()
          setUser(null)
        }}
      />
      <CategoryNav
        active={category}
        onSelect={selectCategory}
        onHowItWorks={howItWorks}
      />

      <main>
        {USE_MOCK && (
          <p className="preview-note container">
            Catalogue preview · Illustrative lots. Bidding is not available yet.
          </p>
        )}
        {!filtering && (
          <>
            <SubscribeBar />
            <CategoryGrid onSelect={selectCategory} />
            <StatsBar />
            <LotGrid
              eyebrow="Last chance"
              title="Closing Soon"
              params={{ sort: 'ending' }}
              limit={4}
              onOpenLot={openLot}
            />
          </>
        )}

        {filtering && (
          <LotGrid
            eyebrow={query ? 'Search results' : 'Browse the vault'}
            title={query ? `“${query}”` : 'Lots'}
            params={{ category, q: query }}
            onOpenLot={openLot}
          />
        )}
      </main>

      {(dialog === 'login' || dialog === 'register') && (
        <Dialog
          title={dialog === 'login' ? 'Sign in' : 'Create account'}
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
      {dialog === 'help' && (
        <Dialog title="How it works" onClose={() => setDialog(null)}>
          <p>
            Create a bidder account to participate, or an auctioneer account to
            manage your lots. This catalogue is a visual preview. Live auctions,
            wallet deposits and bidding will be connected in the next steps.
          </p>
        </Dialog>
      )}
      {lot && (
        <Dialog title={lot.title} onClose={() => setLot(null)}>
          <img className="detail-image" src={lot.image} alt={lot.title} />
          <p className="muted">
            Lot {lot.number} · {lot.categoryName}
          </p>
          <p className="detail-price">{formatMoney(lot.currentBid)}</p>
          <p>Bidding is not available in this preview.</p>
        </Dialog>
      )}
      <footer className="footer">
        <div className="container">© The Yorknew Underground Auction</div>
      </footer>
    </>
  )
}
