# Auction House

Casa de leilões — teste técnico Verzel. Base inicial de qualidade e testes para React/TypeScript e FastAPI/Python; as funcionalidades de leilão ainda serão implementadas.

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

A API expõe `GET /health`. Os testes iniciais verificam o ambiente React/DOM e o endpoint público de saúde. Testes das regras de leilão serão adicionados com a implementação.

As dependências estão fixadas em `package-lock.json` e `backend/uv.lock`. Para adicionar pacotes Python, use `node scripts/uv.mjs add --project backend nome-do-pacote` e inclua o lock atualizado no commit.
