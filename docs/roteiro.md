# Auction House — banco, arquitetura e roteiro

Documento de decisões para implementação. Atualização 28/10/2026: entregas 1–3 integradas à `main` local em `bb20f3b`; entrega 4 commitada e enviada (`fda1e78`); entregas 5, 6 e 7 implementadas no diretório de trabalho, guia em [LANCES_TRANSACIONAIS.md](LANCES_TRANSACIONAIS.md). Prorrogação e produção da outbox antecipadas por pertencerem à transação de aceite; publicação/WebSocket implementados na entrega 5, com uma instância/processo da API. Entrega 1: modelos, migration inicial e Compose de banco/API implementados; guia em [banco-e-docker.md](banco-e-docker.md). Entrega 2: CRUD da própria conta, login/JWT, papéis, consulta da carteira e seed dos três usuários implementados; guia em [crud-inicial.md](crud-inicial.md). O frontend já usa o catálogo persistido e permite importar lotes reais e dar lances. Worker, liquidação, resultados e comprovantes implementados; auditoria pública completa e checkpoints agora implementados na entrega 7. Próxima etapa é finalizar seed aberto e deploy. Guia da entrega 6: [WORKER_LIQUIDACAO_COMPROVANTES.md](WORKER_LIQUIDACAO_COMPROVANTES.md). Fonte de requisitos: PDF do teste técnico Elite Dev da Verzel fornecido nesta conversa.

## 1. Escopo do PDF

Obrigatório: React; backend Python ou Node; banco persistente; deploy público; itens de API pública; leiloeiro e licitante; lances ao vivo; carteira simulada; prorrogação; liquidação; comprovante compartilhável; auditoria pública e privacidade.

O leiloeiro cria e gerencia seus lotes, cancela somente sem lances, consulta resultados e total recebido. Não pode dar lances. O licitante deposita saldo fictício, disputa lotes e consulta participações e arremates.

Telas: vitrine de agendados/ao vivo/encerrados (ocultando cancelados), painel do leiloeiro, sala ao vivo, carteira, meus arremates, comprovante público e auditoria pública. Sala mostra histórico, lance atual, contagem regressiva e indicação de liderança, sem recarregar. Cada recusa deve explicar o motivo.

Entrega: repositório público, link do deploy, README de instalação/uso/limitações e declaração de uso de IA e revisão. Seed: um leiloeiro, dois clientes e ao menos um lote realmente aberto. Prazo: sete dias corridos desde o recebimento; confirmar a data de recebimento antes de fixar o vencimento.

Opcionais: filtros, cancelamento com estorno, Compose, testes e tema escuro. Incluiremos Compose e testes. Cancelar sem lances é obrigatório; cancelar depois de receber lances fica fora da primeira versão. Também ficam fora nota fiscal, revenda, app nativo e recuperação de senha.

## 2. Arquitetura escolhida

React/TypeScript + FastAPI + PostgreSQL + SQLAlchemy/Alembic. Monólito modular com auth, catalog, auctions, wallets e audit.

POO organiza serviços, entidades e repositórios por composição. Os lances também usam serviços e objetos; eventos complementam essa organização.

Fluxo: rota → serviço → transação no banco → commit → evento → atualização WebSocket.

Aceite, reserva e liquidação são transações atômicas. Eventos comunicam fatos confirmados: BidAccepted, AuctionExtended e AuctionClosed. Persistir eventos em outbox na mesma transação do negócio; o publicador da API distribui com retentativas; o worker financeiro só produz o evento de fechamento. Consumidores toleram repetição usando ID do evento e versão do lote. Reconexão recupera estado via HTTP; evento antigo é descartado e lacuna de versão provoca recarga.

Inicialmente uma instância da API. Ela acompanha eventos publicados por cursor e distribui aos WebSockets. Saldo e dados privados não entram em canais públicos. Não precisamos de broker externo nesta primeira topologia.

## 3. Convenções do banco

- PostgreSQL; IDs UUID; dinheiro em centavos BIGINT; moeda BRL.
- Datas TIMESTAMPTZ em UTC; relógio do banco determina validade de lances.
- NOT NULL, FKs, índices, UNIQUE e CHECKs complementam validações do serviço.
- Não excluir registros com histórico financeiro; inativar usuário e restringir exclusões por FK.
- JSONB apenas para atributos externos, snapshot do comprovante e eventos.
- Uma conta tem exatamente um papel; autorização e propriedade sempre conferidas no backend.

## 4. Modelo inicial

| Tabela              | Campos principais e finalidade                                                                                                                                                                                                                         |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| users               | id, public_id UNIQUE, name, email normalizado UNIQUE, password_hash, role, active, created_at                                                                                                                                                          |
| wallets             | id, user_id UNIQUE, balance_cents, reserved_cents; carteira para licitante e para recebimento do leiloeiro                                                                                                                                             |
| lots                | id, seller_id, source_provider, external_item_id, source_url, item_title, item_attributes JSONB, local_image_key, opening_bid_cents, min_increment_cents, starts_at, original_ends_at, ends_at, status, current_bid_id, version, created_at, closed_at |
| bids                | id, lot_id, bidder_id, sequence, amount_cents, accepted_at, previous_hash, record_hash, signature, key_version; somente lances aceitos                                                                                                                 |
| wallet_reservations | id, lot_id, wallet_id, bid_id, amount_cents, status, created_at, released_at; estados active/released/captured                                                                                                                                         |
| wallet_entries      | id, wallet_id, lot_id opcional, bid_id opcional, type, amount_cents, operation_key UNIQUE, request_hash opcional, created_at; razão de depósito/reserva/liberação/débito/crédito                                                                       |
| settlements         | id, lot_id UNIQUE, winning_bid_id UNIQUE, buyer_wallet_id, seller_wallet_id, amount_cents, settled_at                                                                                                                                                  |
| receipts            | id público aleatório, settlement_id UNIQUE, snapshot JSONB, created_at                                                                                                                                                                                 |
| audit_heads         | lot_id PK, last_sequence, last_hash, signature, key_version; cabeçalho autenticado do histórico                                                                                                                                                        |
| outbox_events       | id, lot_id, aggregate_version, event_type, payload JSONB, created_at, published_at, attempts, next_attempt_at                                                                                                                                          |

O lote guarda um snapshot imutável do item importado. Persistir título, atributos e imagem antes da publicação. Falha externa pode impedir nova busca, mas vitrine, sala, auditoria e comprovante continuam disponíveis. Escolher tema/API pública antes dessa integração, verificando limites e autorização de armazenamento das imagens.

Relações: usuário tem uma carteira; leiloeiro tem vários lotes; lote tem vários lances e reservas históricas, no máximo uma reserva ativa. Lote arrematado tem uma liquidação e um comprovante. Participações são consultadas pelos lances.

### Integridade e índices

- Carteira: balance_cents >= 0; 0 <= reserved_cents <= balance_cents. Disponível = total − reservado.
- Lote: valor inicial e incremento > 0; starts_at < original_ends_at; ends_at >= original_ends_at.
- Lance: valor > 0; sequence > 0; UNIQUE(lot_id, sequence).
- Reserva: valor > 0; índice UNIQUE parcial em lot_id quando status = active.
- Lance atual deve pertencer ao próprio lote: FK composta (lot_id, current_bid_id) referenciando bids(lot_id, id), com unicidade correspondente.
- Índices: lots(status, ends_at), lots(seller_id, created_at), bids(bidder_id, accepted_at), reservas(wallet_id, status), outbox pendente de publicação/retentativa.
- Movimentações registram valores positivos; type define efeito sobre saldo total e reservado. Atualizar carteira e razão na mesma transação; testes verificam reconciliação.
- Depósitos recebem chave de idempotência por usuário. Mesma chave/conteúdo retorna resultado anterior; mesma chave com outro conteúdo gera conflito. Liquidação e seus lançamentos também possuem unicidade para evitar duplicação.

## 5. Estados e regras

Estados: scheduled, live, closed e cancelled. Worker atualiza estados, mas o serviço sempre verifica o horário real: starts_at <= agora < ends_at. Lote closed/cancelled nunca aceita lances. A vitrine concilia scheduled/live com os horários para não depender do atraso do worker.

1. Primeiro lance >= valor inicial; próximos >= lance atual + incremento mínimo.
2. Líder não cobre o próprio lance; leiloeiro não oferece lances.
3. Valor inteiro deve caber no disponível.
4. Novo líder reserva saldo; reserva do anterior é liberada na mesma transação.
5. Lance aceito com até 120 segundos restantes define ends_at = horário do aceite + 120 segundos. Decisão interpretativa para “estende o fim para +2 minutos”; explicar no README.
6. Cancelamento somente pelo proprietário, sem nenhum lance e antes do fechamento.
7. Decisão atual: item importado é imutável; valores, categoria e calendário podem ser editados somente antes do início e sem lances. Depois do início, apenas a prorrogação altera ends_at. Esta regra substitui a decisão inicial de bloquear qualquer edição após publicação.
8. Encerramento com vencedor captura reserva, debita vencedor, credita leiloeiro e cria comprovante. Sem lances: encerra sem vencedor, cobrança ou comprovante de arremate.

## 6. Transações críticas

### Lance

1. Autenticar licitante; iniciar transação; bloquear lote com SELECT FOR UPDATE.
2. Bloquear carteiras do ofertante e líder anterior em ordem crescente de ID. Ordem global: lote → carteiras. Operação só de carteira não tenta depois bloquear lote.
3. Após obter locks, consultar relógio do banco e revalidar horário, estado, valor, líder e saldo.
4. Liberar reserva anterior; inserir lance e nova reserva; atualizar carteiras/razão, liderança, prazo, versão e cabeçalho de auditoria.
5. Inserir eventos na outbox e confirmar tudo junto. Qualquer falha desfaz tudo; sucesso HTTP somente após commit.

Lock somente no lote não basta: a mesma carteira pode disputar vários lotes simultaneamente. Lock da carteira impede reservar o mesmo saldo duas vezes. Prever retentativas limitadas para falhas transitórias de concorrência e mensagens claras para recusas de negócio.

### Encerramento

Worker busca vencidos periodicamente e ao reiniciar. Bloqueia lote e revalida ends_at: um lance pode ter prorrogado o prazo. Bloqueia carteiras em ordem consistente e faz liquidação, comprovante, atualização do lote e outbox em uma transação. UNIQUE(lot_id) e chaves de operação impedem cobrança repetida. Fechamento não depende do navegador aberto.

## 7. Auditoria e privacidade

Encadear hashes de representação canônica contendo lote, ID do lance, sequência, identificador público do licitante, valor, horário e hash anterior. Assinar registros e cabeçalho final com HMAC-SHA256; chave fora do banco, via secret, com versão para rotação.

Cabeçalho autentica quantidade e último hash, detectando remoção da cauda. Lote sem lances também possui cabeçalho inicial. Ausência de cabeçalho é falha, não histórico vazio. Endpoint público recalcula cadeia e assinaturas. Não existe CRUD de edição de lances.

Para detectar restauração conjunta de histórico/cabeçalho antigos, worker grava checkpoints autenticados por lote/sequência em journal append-only fora do PostgreSQL. Auditoria compara o maior checkpoint. Até sincronizar, informar checkpoint pendente: não prometer proteção contra rollback do trecho ainda não ancorado.

Limite de ameaça: protege alteração direta no banco sem a chave; acesso à chave permite forjar assinaturas. Volume separado não impede administrador de reescrever banco e journal. Registrar esses limites; não apresentar cadeia de hashes como proteção absoluta.

Auditoria, eventos públicos e comprovantes usam public_id aleatório. Não expor nome, e-mail, saldo ou password_hash. Comprovante contém lote, item, identificador público do vencedor, valor e horário; seu link usa identificador aleatório.

## 8. Docker Compose e persistência

| Serviço  | Responsabilidade                                                           |
| -------- | -------------------------------------------------------------------------- |
| db       | PostgreSQL com healthcheck                                                 |
| migrate  | Aplicar Alembic após db saudável; falha impede início da API/worker        |
| api      | HTTP e WebSocket FastAPI                                                   |
| worker   | Encerrar/liquidar lotes; checkpoints planejados; outbox publicada pela API |
| frontend | Vite em desenvolvimento; build estático em produção                        |

Volumes nomeados:

- pg_data: persistência do banco.
- item_media: imagens importadas; API grava/serve.
- audit_checkpoints: journal separado do banco; worker grava, API lê.

Secrets fora do Git e dos volumes de dados; acesso somente aos processos necessários. Código via bind mount em desenvolvimento, com dependências separadas do host; em produção código incorporado à imagem. Fixar versões de imagens base e usar usuários sem privilégios quando aplicável.

Serviços usam hostname db na rede interna. API/worker aguardam migrations concluídas; db possui healthcheck. Publicar porta do banco ao host somente em desenvolvimento, se necessário.

Critério de aceite: docker compose up --build sobe tudo do zero; seed explícito/idempotente prepara os três usuários e lote aberto sem apagar dados existentes. Reiniciar preserva dados. docker compose down preserva volumes; down -v remove os dados. Volume não substitui backup: documentar exportação/restauração de banco, imagens, journal e chaves.

## 9. Roteiro e critérios de aceite

| Ordem | Entrega                               | Verificação                                                            |
| ----- | ------------------------------------- | ---------------------------------------------------------------------- |
| 1     | Banco, migrations e Compose           | Subir do zero e preservar dados após reinício                          |
| 2     | Autenticação, papéis, carteira e seed | Login de demonstração e recusa de papel incorreto                      |
| 3     | API externa e criação de lote         | Publicar item; simular queda externa e continuar acessando lote/imagem |
| 4     | Depósito e lance transacional         | Reserva, disputa, liberação e recusas corretas                         |
| 5     | Outbox, WebSocket e prorrogação       | Dois navegadores atualizados; reconexão recupera estado                |
| 6     | Worker, liquidação e comprovante      | Fechar sem navegador; repetir worker sem duplicar cobrança             |
| 7     | Auditoria e checkpoints               | Detectar alteração/inserção/remoção direta, inclusive último lance     |
| 8     | Telas restantes, deploy e README      | Percorrer todo o PDF na URL pública; declarar limitações e uso de IA   |

Testes prioritários: lances simultâneos no mesmo lote; mesma carteira em lotes distintos; lance concorrendo com fechamento; reserva liberada; fronteiras de início/fim e prorrogação; liquidação repetida; reinício entre commit e publicação; queda da API externa; auditoria e privacidade. Testes transacionais usam PostgreSQL real para exercitar locks.

## Referências técnicas

- [PostgreSQL: bloqueios de linha](https://www.postgresql.org/docs/17/explicit-locking.html).
- [Docker Compose: inicialização e healthchecks](https://docs.docker.com/compose/how-tos/startup-order/).
- [Docker: persistência PostgreSQL](https://docs.docker.com/guides/postgresql/).

Entrega 7 implementada conforme [AUDITORIA_PUBLICA_CHECKPOINTS.md](AUDITORIA_PUBLICA_CHECKPOINTS.md). Verificação usa snapshot REPEATABLE READ; journal é lido antes do snapshot para evitar falso rollback por avanço concorrente. Checkpoints continuam assíncronos, com estado pendente explícito. README reorganizado para a entrega final; deploy e seed automático de lote aberto ainda pendentes.
