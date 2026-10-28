import { Link, useLocation } from 'react-router-dom'
import { useCountdown } from '../hooks/useCountdown'
import { formatMoney } from '../utils/format'
import type { Lot } from '../types'

interface LotCardProps {
  lot: Lot
}

export default function LotCard({ lot }: LotCardProps) {
  const { search } = useLocation()
  const { label } = useCountdown(lot.endsAt)

  return (
    <Link
      className="lot"
      to={{ pathname: `/lots/${lot.id}`, search }}
      aria-label={`View ${lot.title}`}
    >
      <div className="lot__media">
        <span className="lot__timer">{label}</span>
        <img
          src={lot.image}
          alt={lot.title}
          loading="lazy"
          onError={(e) => {
            e.currentTarget.onerror = null
            e.currentTarget.src = '/images/placeholder.svg'
          }}
        />
      </div>
      <div className="lot__body">
        <span className="lot__meta">
          Lot {lot.number} · {lot.categoryName}
        </span>
        <h3 className="lot__title">{lot.title}</h3>
        <div className="lot__foot">
          <div>
            <span className="lot__label">Lance Atual</span>
            <span className="lot__price">{formatMoney(lot.currentBid)}</span>
          </div>
          <span className="lot__bids">{lot.bids} Lances</span>
        </div>
      </div>
    </Link>
  )
}
