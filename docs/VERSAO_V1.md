# Yorknew — marco v1

Data: 28/10/2026. Marco local anterior à tradução completa e ao catálogo persistente.

## Implementado

- React/TypeScript/Vite: vitrine demonstrativa, categorias, busca, página própria /lots/:id e header persistente.
- Cadastro, login JWT/Argon2, perfil próprio, inativação, leitura de carteira e resumo do leiloeiro no FastAPI.
- PostgreSQL: dez tabelas e migration Alembic 0001. Outbox, reservas, comprovantes e auditoria têm estrutura de banco, ainda sem fluxo de negócio.
- Seed de um leiloeiro e dois licitantes; carteiras zeradas.
- Docker Compose para banco, migrations, API e frontend; volumes de banco, imagens e checkpoints.
- Husky, lint-staged, commitlint, ESLint, Prettier, Ruff, pytest, Vitest e CI.

## O que NÃO está concluído

Catálogo real da API pública; criação/gestão de lotes; depósito e extrato; lances concorrentes/reservas; eventos/WebSocket; worker, prorrogação e liquidação; comprovante e auditoria; deploy público. Os itens visuais da v1 são ilustrativos, não vêm do banco. Não considerar o desafio entregue.

## Validação já existente

42 testes de backend e seis de frontend nas últimas entregas; migrations, build e execução Docker conferidos. Este relatório distingue histórico de validação de checks executados em mudanças futuras.

## UI/UX

A combinação Cormorant Garamond (títulos/preços) e Kumbh Sans (interface) combina com o salão de leilões. Manter a identidade. Corpo com peso 300 e labels de 10–11px exigem esforço de leitura; aumentar peso para 400 e labels para pelo menos 12px. Marrom escuro e ouro têm boa hierarquia; vermelho #c0392b em texto pequeno precisa ser clareado. Ajustar texto suave, foco visível e toque mobile sem trocar a marca.

Referência: WCAG texto comum >=4,5:1: https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum
Esta é uma revisão do CSS e dos componentes, não uma certificação completa de acessibilidade ou teste com usuários.

## Continuação

1. Português em toda interface e feedbacks.
2. Integração de itens públicos e snapshot com imagem persistida.
3. CRUD autorizado dos lotes, consultas públicas e painel do proprietário.
4. Depósito idempotente e extrato.
5. Transações de lance, eventos e encerramento.
6. Auditoria, comprovante e deploy.

Lances e movimentações financeiras não recebem CRUD livre: devem ser registros de operações, preservados para auditoria. Cancelar lote significa atualizar estado; não apagar histórico.
