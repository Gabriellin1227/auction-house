interface NavItem {
  slug: string
  label: string
}

const ITEMS: NavItem[] = [
  { slug: '', label: 'All Lots' },
  { slug: 'jewelry', label: 'Jewelry' },
  { slug: 'fine-art', label: 'Fine Art' },
  { slug: 'horology', label: 'Horology' },
  { slug: 'ceramics', label: 'Ceramics' },
  { slug: 'furniture', label: 'Furniture' },
  { slug: 'coins-manuscripts', label: 'Coins & Manuscripts' },
  { slug: 'curiosities', label: 'Curiosities' },
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
          How it works
        </button>
      </div>
    </nav>
  )
}
