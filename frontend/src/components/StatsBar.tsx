import { fetchStats } from '../api/auction'
import { useAsync } from '../hooks/useAsync'
import { formatMoney } from '../utils/format'

export default function StatsBar() {
  const { data } = useAsync(fetchStats, [])

  const items: { value: string | number; label: string }[] = [
    { value: data?.openLots ?? '–', label: 'Open lots' },
    {
      value: data ? formatMoney(data.valueOnFloor) : '–',
      label: 'Value on the floor',
    },
    { value: data?.bidsPlaced ?? '–', label: 'Bids placed' },
    { value: data ? `${data.hoursOpen} hours` : '–', label: 'Open' },
  ]

  return (
    <section className="container">
      <div className="stats">
        {items.map((it) => (
          <div key={it.label} className="stats__cell">
            <div className="stats__value">{it.value}</div>
            <div className="stats__label">{it.label}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
