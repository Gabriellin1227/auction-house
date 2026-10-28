import { fetchCategories } from '../api/auction'
import { useAsync } from '../hooks/useAsync'
import SectionTitle from './SectionTitle'

interface CategoryGridProps {
  onSelect: (slug: string) => void
}

export default function CategoryGrid({ onSelect }: CategoryGridProps) {
  const { data: categories, loading, error } = useAsync(fetchCategories, [])

  return (
    <section className="section">
      <div className="container">
        <SectionTitle eyebrow="Explore o Cofre" title="Categorias Principais" />
        {error && (
          <p role="alert" className="muted">
            Não foi possivel carregar as categorias. {error.message}
          </p>
        )}
        <div className="catgrid">
          {loading &&
            Array.from({ length: 7 }).map((_, i) => (
              <div key={i} className="catcard skeleton" />
            ))}
          {categories?.map((c) => (
            <button
              key={c.slug}
              className="catcard"
              onClick={() => onSelect(c.slug)}
            >
              <img
                src={c.image}
                alt=""
                loading="lazy"
                onError={(e) => {
                  e.currentTarget.onerror = null
                  e.currentTarget.src = '/images/placeholder.svg'
                }}
              />
              <span className="catcard__name">{c.name}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}
