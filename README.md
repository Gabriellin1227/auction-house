# Yorknew — Auction House

Casa de leilões desenvolvida para o teste técnico Elite Dev da Verzel. Leiloeiros importam obras de uma API pública e publicam lotes; licitantes depositam saldo fictício, disputam por lances e recebem comprovantes públicos. O histórico possui auditoria pública com hashes, HMAC e checkpoints externos ao banco.

Repositório: [Gabriellin1227/auction-house](https://github.com/Gabriellin1227/auction-house). **Deploy público: pendente.** Este README descreve a aplicação local; a entrega do desafio ainda depende do deploy e das pendências ao final.

## Tecnologias e estrutura

React/TypeScript e Vite; FastAPI/Python 3.12; PostgreSQL 17; SQLAlchemy e Alembic. Monólito modular com serviços por composição (POO), transações financeiras e eventos persistidos em outbox. Worker Python separado para fechamento e checkpoints. Atualizações da sala por WebSocket.

- `frontend/src`: páginas, componentes, API client e hooks.
- `frontend/public`: imagens locais e créditos.
- `backend/app`: auth, users, catalog, lots, bids, wallets, settlements, audit e events.
- `backend/migrations`: migration inicial das dez tabelas.
- `backend/tests` e `frontend/test`: testes automatizados.
- `docs/`: guias das entregas e matriz do PDF. A pasta continua ignorada pelo Git por configuração do projeto; este README contém as instruções essenciais para executar um clone.
- Um `package-lock.json` na raiz para JavaScript; `backend/uv.lock` para Python.

## Iniciar com Docker

Requisitos: Git, Docker Engine com Compose e Node 24/npm para os scripts. Os builds de frontend e backend acontecem nos containers; não é necessário instalar Python no host para esse caminho.

```sh
git clone https://github.com/Gabriellin1227/auction-house.git
cd auction-house
npm run setup:env
npm run docker:up
npm run docker:seed
```

`setup:env` cria `.env` com chaves privadas aleatórias quando ausentes e preserva chaves existentes. Não inclua `.env` no Git. `docker:up` aguarda PostgreSQL, aplica migrations e sobe API, worker e frontend.

| Acesso                           | Endereço local              |
| -------------------------------- | --------------------------- |
| Site                             | http://localhost:5174       |
| Swagger / API                    | http://localhost:8000/docs  |
| Saúde / disponibilidade do banco | `/health` e `/ready` na API |
| Banco para ferramentas do host   | `localhost:5433`            |

```sh
docker compose ps
docker compose logs worker
npm run docker:down
```

`docker:down` preserva volumes. `docker compose down -v` remove os dados; não use como reinício comum.

### Contas de demonstração

| Papel     | E-mail                  |
| --------- | ----------------------- |
| Leiloeiro | `leiloeiro@example.com` |
| Licitante | `cliente1@example.com`  |
| Licitante | `cliente2@example.com`  |

Senha pública de demo: `DemoAuction2026!`. Seed idempotente: não redefine senha, ativo ou saldo de contas existentes. Use essas contas somente no ambiente de demonstração.

O seed também importa uma obra real do Cleveland, com imagem persistida, abertura de R$ 10, incremento de R$ 1 e duração de 24 horas. Reutiliza um lote demo aberto com mais de cinco minutos restantes e auditoria válida, sem alterar lances ou prazos existentes. Na primeira importação, precisa acessar o museu; se a origem falhar, preserva as contas e termina com erro, sem criar um lote fictício. Execute novamente após a recuperação. O serviço de seed no Docker compartilha o volume de imagens com a API.

## Roteiro de uso

1. Entre como leiloeiro e abra Minha conta. Busque uma obra no acervo público, selecione e defina categoria, valores, início e fim. Para disputar agora, início deve estar no passado e fim no futuro.
2. Abra dois navegadores/perfis e entre com os dois licitantes. Cada um deposita saldo simulado em Minha conta.
3. Abra o lote. O primeiro lance deve atingir o valor inicial; os próximos devem atingir o atual mais o incremento. A sala atualiza preço, histórico, prazo e liderança automaticamente.
4. Confira a carteira: o líder tem saldo reservado. Quando é superado, sua reserva do lote é liberada na mesma transação do novo lance.
5. Ao vencer o prazo, o worker encerra mesmo sem navegador. Com vencedor, captura a reserva, debita comprador e credita leiloeiro. Sem lances, encerra sem cobrança ou comprovante de arremate.
6. Em Minha conta, licitante consulta participações/arremates e abre o comprovante público. Vendedor consulta resultados por lote e total recebido. Use os botões de atualização da conta para recarregar esses resultados.
7. Compartilhe `/receipts/{uuid}`; funciona sem login e sem expor nome/e-mail/saldo. O lote e o comprovante têm link para `/lots/{uuid}/audit`.
8. Na auditoria, confira cadeia, cabeçalho e checkpoint. **Cadeia válida com checkpoint pendente não significa histórico integralmente ancorado.** A verificação pode ser refeita pelo botão da página.

A barra superior contém somente as sete categorias principais. Para voltar à vitrine sem filtro, clique no logotipo. As imagens de categorias ficam no frontend e têm créditos em `frontend/public/images/categories/credits.json`.

## Regras importantes

- Conta tem um papel; leiloeiro não dá lance. Propriedade, papel e ativo são conferidos no backend.
- Valores em centavos inteiros, BRL. Datas em UTC; o relógio do PostgreSQL decide `início <= agora < fim`.
- Líder não cobre o próprio lance. Disponível = total − reservado, considerando os outros lotes.
- Aceite bloqueia lote e carteiras, em ordem consistente. Lance, reserva/liberação, extrato, prazo, assinatura e outbox confirmam juntos.
- Lance nos últimos 120 segundos redefine o fim para **horário do aceite + 120 segundos**, preservando o prazo original. Essa é a interpretação adotada para a prorrogação do PDF.
- Lote pode ser editado somente antes do início e sem lances; item importado é imutável. Cancelamento lógico somente sem lances e antes do fechamento.
- Depósito tem `Idempotency-Key` UUID: repetir pedido igual não duplica crédito; mesma chave com valor diferente gera conflito.
- Lance não tem chave de idempotência. Se perder a resposta, consulte lote, histórico e carteira antes de reenviar. Só deadlock/serialização com transação abortada têm retentativas automáticas, até três tentativas.
- Liquidação tem unicidade por lote e chaves únicas de débito/crédito. Reexecução não duplica pagamento.
- Inativação preserva histórico; compromissos aceitos continuam sujeitos à liquidação.
- Saldos e comprovantes são de demonstração; não há pagamento real nem nota fiscal.

## API pública e privada

| Método / rota                                                  | Finalidade / acesso                                    |
| -------------------------------------------------------------- | ------------------------------------------------------ |
| `POST /users`, `POST /auth/token`                              | Cadastro e login                                       |
| `GET/PATCH/DELETE /users/me`                                   | Perfil da própria conta; DELETE inativa                |
| `GET /categories`, `GET /lots`, `GET /lots/{id}`, `GET /stats` | Catálogo público                                       |
| `GET /catalog/items?q=...`                                     | Busca externa, leiloeiro                               |
| `POST /lots`, `GET /lots/mine`, `PATCH/DELETE /lots/{id}`      | Gestão de lotes com papel/propriedade                  |
| `GET /wallets/me`, `GET /wallets/me/entries`                   | Carteira e extrato privados                            |
| `POST /wallets/me/deposits`                                    | Depósito simulado, licitante; Idempotency-Key          |
| `POST /lots/{id}/bids`                                         | Lance autenticado, `{ "amount_cents": 8000 }`          |
| `GET /lots/{id}/bids?after=0`                                  | Histórico público; até 100, cursor por sequência       |
| `WS /ws/lots/{id}`                                             | Avisos públicos da sala; frontend acessa `/api/ws/...` |
| `GET /bidders/me/participations?offset=0`                      | Participações próprias, até 100                        |
| `GET /auctioneers/me/summary`                                  | Resultado agregado do próprio vendedor                 |
| `GET /receipts/{id}`                                           | Snapshot público do comprovante                        |
| `GET /lots/{id}/audit?after=0`                                 | Auditoria pública completa; pagina só a exibição       |

Swagger contém schemas e contratos. O token fica em memória: atualizar a página exige novo login. Não há CRUD livre de lance, movimentação, liquidação ou comprovante.

## Persistência e independência da API externa

A importação usa o [acervo aberto do Cleveland Museum](https://www.clevelandart.org/open-access-api), selecionando itens CC0. O backend consulta o item por ID, valida a origem da imagem e persiste título, atributos e JPEG antes de publicar. Vitrine, sala, auditoria e comprovante não precisam consultar o museu para ler itens já publicados. Falha externa pode impedir novas buscas/importações.

| Volume              | Responsabilidade                                                          |
| ------------------- | ------------------------------------------------------------------------- |
| `pg_data`           | PostgreSQL                                                                |
| `item_media`        | Imagens importadas, servidas pela API                                     |
| `audit_checkpoints` | Journal separado do banco; worker escreve, API lê em modo somente leitura |

Volume não é backup. Preserve dump, imagens, journal e chaves privadas em cópias coordenadas. Backups/restauração de produção ainda não foram automatizados.

## Auditoria e limites de ameaça

Cada lance tem SHA-256 de JSON canônico com hash anterior e HMAC-SHA256 autenticado com `AUDIT_SECRET`. Cabeçalho assinado autentica quantidade e hash final, inclusive histórico vazio. A verificação pública examina sequência, dados, assinaturas, cabeçalho e liderança.

O worker grava checkpoints encadeados/autenticados em JSONL fora do PostgreSQL, com locks e fsync. A auditoria compara o journal preservado com o banco para detectar rollback de histórico/cabeçalho antigos. A página distingue resultado válido, inconsistente, indisponível e checkpoint pendente.

Limites: checkpoint é assíncrono; trecho ainda pendente não tem garantia contra rollback. Apagar todo o journal aparece como pendente, não como ancorado. Quem controla banco e journal pode truncar/restaurar ambos; quem obtém a chave pode forjar assinaturas. HMAC não é assinatura digital com chave pública e a API de verificação precisa ser confiável. O mecanismo cobre lances, não autentica todo campo do banco nem assina o comprovante nesta versão. Chave versão 1; rotação ainda não implementada.

### Dados legados e comandos de auditoria

Novos lotes já têm cabeçalho inicial. Para lotes anteriores realmente vazios, é possível criar explicitamente os cabeçalhos ausentes:

```sh
docker compose exec worker python -m app.audit.checkpoints --init-empty-heads
docker compose exec worker python -m app.audit.checkpoints
```

O bootstrap não reassina lances existentes. Não o use para esconder uma falha: histórico com lances e cabeçalho perdido requer investigação/backup confiável.

Fora do Docker: `npm run audit:init-empty` e `npm run audit:checkpoint`. O journal do host usa `backend/audit/`; não é automaticamente o journal do volume Docker. A implementação usa filesystem POSIX; prefira Linux/Docker ou WSL.

## Desenvolvimento sem containers para API/frontend

Requisitos: Node 24 (`nvm use`), Python 3.12, uv 0.13.6 e PostgreSQL. Você pode usar o serviço db do Compose.

```sh
npm ci
npm run setup:env
npm run setup:backend
npm run db:up
npm run db:migrate
npm run db:seed
```

Em terminais separados:

```sh
node scripts/uv.mjs run --directory backend --locked uvicorn app.main:app --reload
npm run worker
npm run dev
```

Site em http://localhost:5173. Vite encaminha `/api` para a API em localhost:8000, incluindo WebSocket. `npm run worker:once` executa um ciclo. `npm run build` gera o frontend; `npm run preview` é prévia estática, sem proxy da API.

`VITE_USE_MOCK=false` é o padrão. `true` é só prévia visual, explicitamente identificada e sem lances reais. Não existe fallback silencioso para dados fictícios.

### Variáveis principais

Veja `.env.example`. Não publique segredos.

| Variável                         | Uso                                                             |
| -------------------------------- | --------------------------------------------------------------- |
| `DATABASE_URL`                   | Runtime PostgreSQL                                              |
| `DATABASE_URL_UNPOOLED`          | Conexão direta para migrations, útil no Neon                    |
| `AUTH_SECRET`                    | Assinatura JWT                                                  |
| `AUDIT_SECRET`                   | HMAC de lances, cabeçalhos e checkpoints; preservar com backups |
| `ACCESS_TOKEN_MINUTES`           | Expiração JWT, padrão 30                                        |
| `EVENTS_ENABLED`                 | Publicador da outbox, padrão true                               |
| `AUDIT_DIR` / `MEDIA_DIR`        | Diretórios de journal e imagens                                 |
| `VITE_API_URL` / `VITE_USE_MOCK` | Base da API / prévia visual                                     |

O Compose configura URLs internas usando hostname `db`. No host, a porta padrão é 5433. No Neon, preserve TLS (`sslmode=require`) e use conexão direta para migrations. Neon/Vercel ainda não representam um deploy concluído desta aplicação.

## Testes e automações

```sh
npm ci
npm run setup:backend
npm run db:up
TEST_DATABASE_URL=postgresql://auction:auction_dev@localhost:5433/auction_house npm run check
npm run build
```

A URL acima é exclusiva de desenvolvimento local. Testes PostgreSQL usam schemas temporários e os removem ao final; não adulteram o schema demo. Sem `TEST_DATABASE_URL`, testes de integração são pulados e não validam locks. Para o ambiente de teste Docker: `npm run db:test`.

Validação local mais recente: **118 testes backend e 22 frontend aprovados**, além de lint, formatação, tipagem e build.

Cobertura inclui autenticação/papéis, CRUDs, snapshot offline, depósito idempotente, reserva/liberação, concorrência, prorrogação, rollback, liquidação repetida, dois workers, reconexão, privacidade, adulteração de lances, remoção de cauda/meio e rollback com checkpoint preservado.

Husky/lint-staged: formatação/lint no pre-commit, Conventional Commits no commit-msg e `npm run check` no pre-push. CI repete frontend/backend/build e valida mensagens em PRs. Nenhum hook cria commits automaticamente.

## Publicação gratuita em preparação

A opção escolhida é **Vercel + Neon + Northflank Sandbox**, condicionada à disponibilidade de volume persistente dentro da franquia gratuita. Vercel e Neon já estão autenticados; o banco isolado do leilão foi criado. Cadastro/acesso ao Northflank e publicação ainda estão pendentes. Nenhum serviço pago do Render foi criado; o `render.yaml` abaixo é somente uma alternativa paga.

O compute Neon foi fixado em 0,25 CU. O worker mantém o banco ativo: a franquia anunciada de 100 CU-h por projeto equivale a cerca de 400 horas nesse tamanho, não um mês inteiro de operação contínua. Não habilitar cobrança automática para ampliar essa franquia.

Roteiro e limites: [deploy gratuito](docs/DEPLOY_GRATUITO.md). **Ainda não há URL pública desta aplicação.**

## Publicação preparada: Vercel, Neon e Render

A configuração está no código; **a aplicação ainda não foi publicada**.

- Vercel: raiz do repositório, Node 24, `npm ci`, `npm run build`, saída `frontend/dist`. `vercel.json` configura o fallback das páginas React.
- Frontend: `VITE_USE_MOCK=false` e `VITE_API_URL=https://SEU-SERVICO.onrender.com`, sem `/api`. Reconstruir o frontend ao alterar essas variáveis.
- Neon: `DATABASE_URL` com TLS e `DATABASE_URL_UNPOOLED` com a conexão direta para migrations; preservar os parâmetros fornecidos pelo painel.
- Render: `render.yaml` usa plano pago `starter` e disco persistente de 1 GB em `/data`. Confirmar custo antes de provisionar. O Dockerfile é `backend/Dockerfile.render`, com contexto `backend/`.
- Backend: `CORS_ORIGINS=["https://SEU-PROJETO.vercel.app"]`, chaves independentes `AUTH_SECRET`/`AUDIT_SECRET`, `MEDIA_DIR=/data/media`, `AUDIT_DIR=/data/audit`, `WORKER_REQUIRED=true`, `EVENTS_ENABLED=true`.

O comando `python -m app.deploy` aplica migrations antes de iniciar API e worker juntos. Se um processo terminar, o supervisor encerra o serviço; `/ready` confere banco e heartbeat do worker. Um serviço único permite que ambos acessem o disco Render. Deploys com esse disco têm pausa; não escalar para múltiplas instâncias.

Após publicar, executar `python -m app.seed --demo` no **Shell do serviço Render em execução**, com acesso ao disco. Executar seed local contra o Neon não transfere as imagens para o Render. Conferir lote aberto, imagens, login/depósitos, disputa em duas sessões, WebSocket, liquidação, comprovante e auditoria pelo domínio público.

Para banco remoto novo, o Blueprint pode gerar chaves novas. Ao transferir histórico existente, preservar a chave de auditoria correspondente, o journal e as imagens. Não publicar credenciais de banco/chaves no frontend ou Git.

## Estado da entrega e pendências

Implementados localmente: contas, catálogo persistido, lotes, carteira, lances, eventos/WebSocket, worker, liquidação, comprovantes, participações/resultados e auditoria com checkpoints.

Ainda faltam:

- Deploy público e validação dos fluxos na URL de entrega.
- Provisionar e validar Render com API/worker e disco persistente; `render.yaml` e `backend/Dockerfile.render` estão preparados. A topologia atual suporta **uma instância/processo da API**; não aumentar workers/réplicas sem barramento compartilhado.
- Revisão humana final e conferência completa do PDF no ambiente público.
- Backups operacionais e teste de recuperação, rotação de chaves e revisão ampla de acessibilidade.

Cancelamento com estorno após lances e tema claro são opcionais e não foram implementados. Recuperação de senha, nota fiscal, revenda e aplicativo nativo ficam fora do escopo indicado no desafio.

## Uso de IA e revisão

IA foi utilizada para apoiar a estruturação do projeto, implementação de backend/frontend, testes e documentação, a partir das decisões e solicitações do desenvolvedor. As validações automatizadas executadas estão registradas nos guias de cada entrega. A revisão humana final e a validação do deploy ainda precisam ser concluídas pelo responsável antes do envio; este texto não declara que essas etapas já ocorreram.

Documentação local complementar: `docs/ENTREGAS.md`, `docs/MATRIZ_REQUISITOS_PDF.md` e `docs/AUDITORIA_PUBLICA_CHECKPOINTS.md`.
