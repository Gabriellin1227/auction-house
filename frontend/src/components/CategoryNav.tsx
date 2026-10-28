interface NavItem {
  slug: string
  label: string
}

const ITEMS: NavItem[] = [
  { slug: '', label: 'All Lots' },
  { slug: 'jewelry', label: 'Joias' },
  { slug: 'fine-art', label: 'Arte Moderna' },
  { slug: 'horology', label: 'Relojoaria' },
  { slug: 'ceramics', label: 'Ceramica' },
  { slug: 'furniture', label: 'Mobília' },
  { slug: 'coins-manuscripts', label: 'Moedas & Manuscritos' },
  { slug: 'curiosities', label: 'Curiosidades' },
]

interface CategoryNavProps {
  active: string
  onSelect: (slug: string) => void
  onHowItWorks: () => void
}

export default function CategoryNav({
  active,
  onSelect,
  onHowItWorks,
}: CategoryNavProps) {
  return (
    <nav className="catnav" aria-label="Categories">
      <div className="container catnav__row">
        <ul className="catnav__list">
          {ITEMS.map((item) => (
            <li key={item.slug}>
              <button
                className={`catnav__item ${active === item.slug ? 'is-active' : ''}`}
                onClick={() => onSelect(item.slug)}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
        <button className="catnav__item" onClick={onHowItWorks}>
          Como isso funciona
        </button>
      </div>
    </nav>
  )
}
