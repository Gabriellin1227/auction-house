# Entrega 1 — banco e migrations

## O que está pronto

Dez tabelas do roteiro implementadas com SQLAlchemy e migration Alembic `0001`: users, wallets, lots, bids, wallet_reservations, wallet_entries, settlements, receipts, audit_heads e outbox_events.

O PostgreSQL aplica restrições de saldo, valores positivos, estados, datas, unicidade de e-mail normalizado, sequência de lances, reserva ativa por lote, liquidação por lote e comprovante por liquidação. FKs compostas impedem associar lance atual, reserva ou liquidação a outro lote. Exclusões que quebrariam histórico são recusadas.

Lances, liquidação, autenticação, geração/verificação de assinaturas, seed, processamento da outbox e worker serão implementados nas próximas entregas. Ter suas tabelas não significa que esses fluxos já funcionem. A API expõe `/health` para processo vivo e `/ready` para conexão com o banco; `/ready` não é uma verificação de integridade das migrations.

## Subir tudo com Docker

Requisito: Docker Engine e plugin Compose. Na raiz:

```sh
npm run setup:env
npm run docker:up
```

Também funciona diretamente com `docker compose up -d --build --wait api`. O Compose fornece valores locais padrão caso `.env` ainda não exista. São credenciais de desenvolvimento; não reutilizar no deploy.

Ordem automática: PostgreSQL saudável → migrate aplica `upgrade head` → API inicia. A API usa a imagem de produção sem dependências de teste, com usuário não root. O container de migration termina com código 0; é esperado.

- Documentação interativa: http://localhost:8000/docs
- Conexão do banco para ferramentas locais: host localhost, porta 5433, database auction_house, usuário auction, senha auction_dev (ou os valores alterados em `.env`).
- Dentro da rede Docker, o banco é `db:5432`, não localhost.

```sh
docker compose ps -a
docker compose logs api migrate
npm run docker:down
```

Apenas db, migrate e api estão ativos nesta entrega. Worker e frontend serão adicionados quando seus comportamentos existirem; não há serviços vazios fingindo executá-los.

## Volumes

| Volume            | Uso                                                                                 |
| ----------------- | ----------------------------------------------------------------------------------- |
| pg_data           | Dados PostgreSQL 17 em `/var/lib/postgresql/data`                                   |
| item_media        | Arquivos dos itens em `/data/media`; estrutura preparada para próxima integração    |
| audit_checkpoints | `/data/audit`, leitura na API; gravação será ligada ao worker na etapa de auditoria |

Os volumes sobrevivem a `docker compose down`. `docker compose down -v` apaga os dados; não faz parte do fluxo normal. Alterar POSTGRES_USER/PASSWORD/DB depois da primeira inicialização não muda automaticamente os usuários do volume existente. Escolher credenciais antes de iniciar ou alterá-las via SQL.

Volumes locais não substituem backup nem são transferidos automaticamente para Vercel, Neon ou outro host. Quando o deploy usar API e worker separados, imagens/checkpoints precisarão de armazenamento persistente acessível por ambos, por exemplo object storage; não presumir compartilhamento de disco entre serviços.

## Desenvolver Python no host

```sh
npm ci
npm run setup:backend
npm run db:up
npm run db:migrate
node scripts/uv.mjs run --project backend --locked uvicorn app.main:app --app-dir backend --reload
```

Não iniciar a API no host e no Docker na mesma porta simultaneamente. As configurações são lidas das variáveis do processo, `.env` da raiz e `backend/.env` (este último tem precedência entre arquivos).

## Criar e aplicar migrations

```sh
npm run db:current
node scripts/uv.mjs run --project backend --locked alembic -c backend/alembic.ini revision --autogenerate -m "descreve a alteracao"
npm run db:migrate
npm run db:check
```

Editar modelos primeiro, gerar a migration, revisar o SQL e só depois aplicá-la. Não usar `Base.metadata.create_all()` como substituto das migrations. Migration publicada não deve ser editada; criar uma nova. A FK circular entre lotes e lance atual é criada explicitamente depois das duas tabelas e removida antes do rollback.

Rollback de desenvolvimento, somente em banco descartável, remove tabelas/dados desta entrega:

```sh
node scripts/uv.mjs run --project backend --locked alembic -c backend/alembic.ini downgrade base
```

Para executar SQL em ferramenta gráfica, conectar no banco acima. Para consultar o esquema pelo terminal:

```sh
docker compose exec db psql -U auction -d auction_house -c '\dt'
```

## Testes e CI

```sh
npm run db:test
```

Esse comando constrói uma imagem de teste e roda contra PostgreSQL real. Cada teste usa um schema `test_<uuid>` temporário, removido ao final; não apaga as tabelas públicas. A credencial de teste precisa ter permissão para criar schemas. Usar banco de desenvolvimento/teste, nunca a URL de produção.

Sem Docker para Python, com PostgreSQL local já rodando:

```sh
TEST_DATABASE_URL=postgresql://auction:auction_dev@localhost:5433/auction_house npm run backend:test
```

Sem TEST_DATABASE_URL, testes de banco são explicitamente marcados como skipped; os testes unitários/HTTP continuam rodando nos hooks. No GitHub Actions, PostgreSQL é obrigatório e configurado como serviço: aplica migrations, verifica divergência dos modelos e roda toda a suíte.

Cobertura de comportamento nesta entrega: upgrade/downgrade/upgrade, repetição de upgrade, comparação entre modelo e esquema real, restrições financeiras e FKs, rollback conjunto de carteira/outbox, bloqueio entre transações, configuração TLS e mensagens de indisponibilidade sem vazamento de conexão.

## Neon e Vercel

Podemos manter React na Vercel e PostgreSQL no Neon. O backend está preparado para receber duas variáveis privadas:

```dotenv
DATABASE_URL=postgresql://USER:ENCODED_PASSWORD@POOLED_HOST/DB?sslmode=require
DATABASE_URL_UNPOOLED=postgresql://USER:ENCODED_PASSWORD@DIRECT_HOST/DB?sslmode=require
```

A aplicação usa DATABASE_URL. Alembic prefere DATABASE_URL_UNPOOLED e, na ausência dela, usa DATABASE_URL. Usar URL direta para migrations, inclusive com conexão pooled na aplicação. O código normaliza o driver para psycopg sem perder parâmetros TLS ou caracteres codificados da senha. Não colocar URLs do banco em variáveis VITE_* ou no navegador.

Procedimento futuro: criar uma branch Neon de teste; configurar as duas URLs no ambiente privado; aplicar a migration uma vez com Alembic; executar os testes nessa branch descartável; depois repetir a migration no ambiente escolhido de produção, com backup apropriado. Não executar migrations automaticamente em cada requisição HTTP ou ao importar a aplicação.

A documentação atual da Vercel suporta WebSocket em FastAPI/ASGI, com Fluid compute, mas cada conexão termina ao atingir a duração máxima da Function. Reconexão e recuperação de estado continuam obrigatórias. Encerramento de leilões e outbox exigem execução independente de visitas: manter a opção de API/worker Docker em host com processos contínuos. A escolha do host e do armazenamento compartilhado será fechada na etapa de deploy; esta entrega não cria recursos pagos ou banco remoto.

Fontes consultadas:

- [Neon com SQLAlchemy](https://neon.com/docs/guides/sqlalchemy).
- [Neon: connection pooling](https://neon.com/docs/connect/connection-pooling).
- [Vercel: WebSockets e FastAPI](https://vercel.com/docs/functions/websockets).
- [Render: workers contínuos](https://render.com/docs/background-workers).
