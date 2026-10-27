/** Monetary values are integer BRL cents, matching FastAPI. */
export const formatMoney = (cents: number): string =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(
    cents / 100,
  )
