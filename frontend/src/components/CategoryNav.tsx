interface NavItem {
  slug: string
  label: string
}

const ITEMS: NavItem[] = [
  { slug: 'jewelry', label: 'Joias' },
  { slug: 'fine-art', label: 'Belas-artes' },
  { slug: 'horology', label: 'Relojoaria' },
  { slug: 'ceramics', label: 'Cerâmica' },
  { slug: 'furniture', label: 'Mobília' },
  { slug: 'coins-manuscripts', label: 'Moedas e manuscritos' },
  { slug: 'curiosities', label: 'Curiosidades' },
]

interface CategoryNavProps {
  active: string
  onSelect: (slug: string) => void
}

export default function CategoryNav({ active, onSelect }: CategoryNavProps) {
  return (
    <nav className="catnav" aria-label="Categorias">
      <div className="container catnav__row">
        <ul className="catnav__list">
          {ITEMS.map((item) => (
            <li key={item.slug}>
              <button
                className={`catnav__item ${active === item.slug ? 'is-active' : ''}`}
                aria-pressed={active === item.slug}
                onClick={() => onSelect(item.slug)}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  )
}
