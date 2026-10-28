# Auction House

A documentação de acompanhamento fica localmente em `docs/STATUS_PROJETO.md` e `docs/VERSAO_V1.md` (a pasta `docs/` está ignorada pelo Git). O documento do marco histórico também pode ser consultado com `git show v1:VERSAO_V1.md`.

Casa de leilões — teste técnico Verzel. Base com PostgreSQL, modelos SQLAlchemy, migrations Alembic, Docker Compose e automações de qualidade para React/TypeScript e FastAPI/Python. CRUDs de contas e lotes, catálogo público e depósitos simulados estão implementados. Lances, eventos, liquidação e auditoria permanecem nas próximas entregas.

## Frontend Yorknew

O visual de `yorknew-auction.zip` foi integrado em `frontend/src` com Vite, mantendo React/TypeScript e as automações da raiz. Há um único package-lock.json para JavaScript e uv.lock separado para Python.

```sh
npm ci
npm run dev
```

Abra http://localhost:5173. Para login/cadastro reais, mantenha FastAPI em localhost:8000; o Vite encaminha `/api` ao backend removendo esse prefixo. Use as contas demo abaixo ou cadastre uma conta. O token fica apenas na memória: atualizar a página exige novo login.

O catálogo usa o PostgreSQL por padrão (`VITE_USE_MOCK=false`). Leiloeiros importam itens CC0 do acervo público Cleveland pela página Minha conta; título, atributos e imagem são persistidos. A vitrine não depende da API externa para exibir os lotes já publicados. `VITE_USE_MOCK=true` habilita explicitamente a prévia visual de desenvolvimento.

Minha conta também oferece edição de perfil, consulta de carteira/extrato e depósito simulado idempotente para licitantes. O painel do leiloeiro cria, edita lotes agendados sem lances e cancela lotes sem lances. Lances/worker/liquidação/auditoria ainda estão nas próximas entregas.

Configuração opcional em frontend/.env (base em frontend/.env.example): VITE_API_URL=/api e VITE_USE_MOCK=false. Não há fallback silencioso para dados fictícios quando a API real falha.

Build: `npm run build`; preview do build: `npm run preview` (a prévia estática não inclui o proxy de desenvolvimento). O CI verifica também o build. No Docker, `npm run docker:up` sobe API, banco e frontend; abra http://localhost:5174. O Nginx encaminha `/api` à API no ambiente Docker.

## Banco e API com Docker

```sh
npm run setup:env
npm run docker:up
npm run docker:seed
```

Requer Docker e Compose. PostgreSQL aguarda ficar saudável, Alembic aplica migrations e FastAPI sobe em http://localhost:8000/docs. Dados persistem em volumes nomeados. Para parar preservando dados: `npm run docker:down`.

Detalhes de banco, migrations, volumes, testes e preparação do Neon: [guia da entrega 1](docs/banco-e-docker.md). Decisões e próximas etapas: [roteiro](docs/roteiro.md).

Para testar as restrições em PostgreSQL real: `npm run db:test`. O CI também executa esses testes. Sem `TEST_DATABASE_URL`, os testes de integração são marcados como skipped no fluxo local.

## CRUD e login para testar

A API já permite cadastro com carteira, login, consulta/edição do perfil e inativação da própria conta. Há também consulta da carteira e resumo restrito ao leiloeiro. Guia com rotas, exemplos e passo a passo no Swagger: [CRUD inicial](docs/crud-inicial.md).

Após rodar `npm run docker:seed`, use no **Authorize** de http://localhost:8000/docs:

- `leiloeiro@example.com` (auctioneer)
- `cliente1@example.com` e `cliente2@example.com` (bidder)
- Senha pública de demonstração para os três: `DemoAuction2026!`

Seed não altera contas existentes nem cria lote fictício. O lote de demonstração pode ser importado pelo painel do leiloeiro, a partir da API pública. Tokens expiram em 30 minutos e exigem AUTH_SECRET privada; `setup:env` gera a chave localmente.

## Preparação

Requisitos: Node 24 (`nvm use`), Python 3.12 e uv 0.13.6 no PATH.
Para instalar uv: `python3 -m pip install --user uv==0.13.6` (ou use o instalador oficial em https://docs.astral.sh/uv/getting-started/installation/).

Na raiz:

```sh
npm ci
npm run setup:backend
npm run check
```

`npm ci` ativa os hooks do Husky automaticamente. Nesta máquina há também uma cópia de uv em `.tools/bin/uv`, ignorada pelo Git; o runner usa essa cópia quando disponível.

## Commits e validações

- `pre-commit`: lint-staged executa ESLint/Prettier nos arquivos JS/TS e Ruff nos arquivos Python staged. Correções são incluídas no commit.
- `commit-msg`: commitlint exige Conventional Commits, por exemplo `feat: adiciona carteira`, `fix: corrige reserva de saldo` ou `chore: configura ferramentas`.
- `pre-push`: executa `npm run check`, com formatação, lint, tipagem e testes de ambas as partes.
- GitHub Actions: valida frontend e backend em pushes e pull requests; em pull requests também valida as mensagens dos commits da contribuição.

Os hooks validam commits feitos por você; eles não criam commits nem fazem push automaticamente. O CI repete as verificações mesmo se um hook local for desativado. Para exigir CI antes do merge, habilite proteção da branch no GitHub.

## Comandos

| Comando                                                                                     | Objetivo                           |
| ------------------------------------------------------------------------------------------- | ---------------------------------- |
| `npm run format`                                                                            | Formatar arquivos com Prettier     |
| `npm run lint`                                                                              | ESLint sem warnings                |
| `npm run typecheck`                                                                         | Validar TypeScript                 |
| `npm test`                                                                                  | Testes frontend com Vitest         |
| `npm run test:watch`                                                                        | Testes frontend em modo interativo |
| `npm run check:frontend`                                                                    | Todas as verificações frontend     |
| `npm run check:backend`                                                                     | Ruff e pytest                      |
| `npm run check`                                                                             | Todas as verificações              |
| `node scripts/uv.mjs run --project backend ruff format backend`                             | Formatar Python                    |
| `node scripts/uv.mjs run --project backend uvicorn app.main:app --app-dir backend --reload` | Iniciar API                        |

A API expõe `GET /health` e `GET /ready` (conexão PostgreSQL). Os testes iniciais verificam o ambiente React/DOM e o endpoint público de saúde. Testes das regras de leilão serão adicionados com a implementação.

As dependências estão fixadas em `package-lock.json` e `backend/uv.lock`. Para adicionar pacotes Python, use `node scripts/uv.mjs add --project backend nome-do-pacote` e inclua o lock atualizado no commit.
