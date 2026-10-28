import { fetchStats } from '../api/auction'
import { useAsync } from '../hooks/useAsync'
import { formatMoney } from '../utils/format'

export default function StatsBar() {
  const { data } = useAsync(fetchStats, [])

  const items: { value: string | number; label: string }[] = [
    { value: data?.openLots ?? '–', label: 'Lotes ao vivo' },
    {
      value: data ? formatMoney(data.valueOnFloor) : '–',
      label: 'Valor em disputa',
    },
    { value: data?.bidsPlaced ?? '–', label: 'Lances registrados' },
    { value: data ? `${data.hoursOpen} horas` : '–', label: 'Funcionamento' },
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
