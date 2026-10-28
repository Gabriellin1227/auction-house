import { USE_MOCK } from '../api/auction'
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
        eyebrow={query ? 'Resultados da busca' : 'Explore o acervo'}
        title={query ? `“${query}”` : 'Lotes'}
        params={{ category, q: query }}
      />
    )
  return (
    <>
      <SubscribeBar />
      <CategoryGrid onSelect={selectCategory} />
      <StatsBar />
      {USE_MOCK ? (
        <LotGrid
          eyebrow="Última oportunidade"
          title="Encerrando em breve"
          params={{ sort: 'ending' }}
          limit={4}
        />
      ) : (
        <>
          <LotGrid
            title="Ao vivo"
            params={{ status: 'live', sort: 'ending' }}
          />
          <LotGrid title="Agendados" params={{ status: 'scheduled' }} />
          <LotGrid title="Encerrados" params={{ status: 'closed' }} />
        </>
      )}
    </>
  )
}
