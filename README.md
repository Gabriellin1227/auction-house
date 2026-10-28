# Auction House

A documentação de acompanhamento fica localmente em `docs/STATUS_PROJETO.md` e `docs/VERSAO_V1.md` (a pasta `docs/` está ignorada pelo Git). O documento do marco histórico também pode ser consultado com `git show v1:VERSAO_V1.md`.

Casa de leilões — teste técnico Verzel. Base com PostgreSQL, modelos SQLAlchemy, migrations Alembic, Docker Compose e automações de qualidade para React/TypeScript e FastAPI/Python. CRUDs de contas e lotes, catálogo público e depósitos simulados estão implementados. Lances transacionais com reserva/liberação de saldo, prorrogação e gravação da outbox estão implementados. Publicação em tempo real, liquidação e auditoria pública permanecem nas próximas entregas.

## Frontend Yorknew

O visual de `yorknew-auction.zip` foi integrado em `frontend/src` com Vite, mantendo React/TypeScript e as automações da raiz. Há um único package-lock.json para JavaScript e uv.lock separado para Python.

```sh
npm ci
npm run dev
```

Abra http://localhost:5173. Para login/cadastro reais, mantenha FastAPI em localhost:8000; o Vite encaminha `/api` ao backend removendo esse prefixo. Use as contas demo abaixo ou cadastre uma conta. O token fica apenas na memória: atualizar a página exige novo login.

O catálogo usa o PostgreSQL por padrão (`VITE_USE_MOCK=false`). Leiloeiros importam itens CC0 do acervo público Cleveland pela página Minha conta; título, atributos e imagem são persistidos. A vitrine não depende da API externa para exibir os lotes já publicados. `VITE_USE_MOCK=true` habilita explicitamente a prévia visual de desenvolvimento.

Minha conta também oferece edição de perfil, consulta de carteira/extrato e depósito simulado idempotente para licitantes. O painel do leiloeiro cria, edita lotes agendados sem lances e cancela lotes sem lances. A página do lote permite enviar lances em centavos, acompanhar liderança e consultar histórico público paginado. Use **Atualizar lote** para consultar a disputa entre clientes; WebSocket, worker, liquidação e auditoria pública ainda estão nas próximas entregas.

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

A API expõe `GET /health` e `GET /ready` (conexão PostgreSQL). A suíte atual tem 70 testes backend (com PostgreSQL real para integração) e dez frontend. Inclui autenticação, CRUDs, depósitos, privacidade, reservas/liberações, recusas de lance, prorrogação, rollback e concorrência no mesmo lote ou na mesma carteira.

As dependências estão fixadas em `package-lock.json` e `backend/uv.lock`. Para adicionar pacotes Python, use `node scripts/uv.mjs add --project backend nome-do-pacote` e inclua o lock atualizado no commit.

## Lances transacionais (entrega 4)

Execute `npm run setup:env` antes de subir a API: além de `AUTH_SECRET`, agora existe `AUDIT_SECRET`, uma chave privada separada para assinar os lances. O comando preserva chaves existentes. Faça backup privado e não substitua a chave de auditoria após ter registros assinados; rotação com múltiplas versões ainda será implementada.

Um licitante autenticado envia `POST /lots/{id}/bids` com `{ "amount_cents": 8000 }` para oferecer R$ 80,00. O primeiro lance precisa atingir o inicial; os próximos, o atual mais o incremento. O líder não cobre o próprio lance. Período válido: início inclusivo, fim exclusivo, usando relógio do banco após adquirir os locks.

O serviço bloqueia lote e carteiras (em ordem de ID), valida saldo disponível e confirma lance, reserva, liberação anterior, extrato, cabeçalho assinado e outbox na mesma transação. O saldo total permanece igual durante a disputa. Lance nos últimos 120 segundos redefine o fim para horário do aceite + 120 segundos, preservando o prazo original.

`GET /lots/{id}/bids?after=0` é público: retorna até 100 lances em ordem crescente; use a última sequência em `after` para continuar. Só expõe identificador público aleatório, valor, sequência, horário e ID do lance. `GET /lots/{id}` inclui `leaderPublicId` e `version`.

Para testar, deposite saldo fictício com os dois clientes e dispute um lote com início passado e fim futuro. Confira as reservas/liberações na carteira. O frontend mostra recusas e liderança; clique em **Atualizar lote** para consultar alterações de outros clientes. A contagem no navegador é indicativa; o banco decide o prazo.

Limites desta etapa: eventos permanecem pendentes na outbox; ainda não há WebSocket, liquidação ou comprovante. Depois do prazo, a reserva do vencedor continua comprometida até implementarmos o worker. Hashes/HMAC já são reais, mas ainda faltam verificação pública completa e checkpoints externos. Não há idempotência no endpoint de lance: se a resposta se perder, consulte histórico e carteira antes de reenviar; somente transações comprovadamente abortadas por deadlock/serialização são repetidas automaticamente, até três tentativas.

Guia local explicado passo a passo: `docs/LANCES_TRANSACIONAIS.md` (pasta ignorada pelo Git). A documentação essencial para clonar e executar permanece neste README.
