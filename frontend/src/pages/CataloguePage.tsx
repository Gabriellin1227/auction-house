import { useOutletContext, useSearchParams } from 'react-router-dom'
import CategoryGrid from '../components/CategoryGrid'
import SubscribeBar from '../components/SubscribeBar'
import StatsBar from '../components/StatsBar'
import LotGrid from '../components/LotGrid'
import type { CatalogueNavigation } from '../App'

export default function CataloguePage() {
  const { selectCategory } = useOutletContext<CatalogueNavigation>()
  const [params] = useSearchParams()
  const category = params.get('category') || ''
  const query = params.get('q') || ''
  const filtering = category !== '' || query !== ''
  if (filtering)
    return (
      <LotGrid
        eyebrow={query ? 'Search results' : 'Browse the vault'}
        title={query ? `“${query}”` : 'Lots'}
        params={{ category, q: query }}
      />
    )
  return (
    <>
      <SubscribeBar />
      <CategoryGrid onSelect={selectCategory} />
      <StatsBar />
      <LotGrid
        eyebrow="Last chance"
        title="Closing Soon"
        params={{ sort: 'ending' }}
        limit={4}
      />
    </>
  )
}
