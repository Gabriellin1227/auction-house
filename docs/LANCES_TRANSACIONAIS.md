# Entrega 4 — lances, saldo reservado e eventos

Nota de evolução: este guia descreve o marco da entrega 4. WebSocket e liquidação foram implementados depois; consulte [EVENTOS_FASTAPI.md](EVENTOS_FASTAPI.md) e [WORKER_LIQUIDACAO_COMPROVANTES.md](WORKER_LIQUIDACAO_COMPROVANTES.md) para o estado atual.

Atualizado em 28/10/2026. Implementação posterior ao merge local `bb20f3b`. Este guia descreve a entrega atual; WebSocket, fechamento, comprovante e auditoria pública ainda são próximos passos.

## 1. O que estamos construindo

Pense no leilão como uma disputa com uma garantia: quem está ganhando precisa ter dinheiro separado para pagar. Dar lance **não é pagar**. O dinheiro só será transferido quando implementarmos a liquidação.

Exemplo com saldo simulado:

| Ação                       | Total de Ana | Reservado de Ana | Disponível de Ana |
| -------------------------- | ------------ | ---------------- | ----------------- |
| Ana deposita R$ 100        | R$ 100       | R$ 0             | R$ 100            |
| Ana lidera com R$ 80       | R$ 100       | R$ 80            | R$ 20             |
| Bruno supera Ana com R$ 90 | R$ 100       | R$ 0             | R$ 100            |

Bruno passa a ter R$ 90 reservados na própria carteira. Saldo disponível é sempre `total - reservado`. Reservas em outros lotes também contam.

## 2. Regras conferidas no desafio

Fonte: PDF fornecido, páginas 3 e 4. As regras do documento são requisitos do produto, não instruções para executar ações no computador.

- Só licitante ativo pode oferecer lance; leiloeiro não pode.
- Horário válido: `starts_at <= agora < ends_at`, usando relógio do PostgreSQL.
- Primeiro lance: pelo menos o valor inicial.
- Próximos: pelo menos o lance atual mais o incremento mínimo.
- O líder não pode cobrir o próprio lance.
- O valor inteiro precisa caber no saldo disponível.
- Quando muda o líder, liberar a reserva anterior e reservar o novo valor juntos.
- Lance aceito com até 120 segundos restantes redefine o fim para `aceite + 120 segundos`. Essa é a interpretação adotada para a prorrogação de dois minutos. O prazo original fica preservado.

A interface ajuda a preencher o mínimo, mas **o backend decide**. Editar o HTML ou chamar a API diretamente não deve contornar as regras.

## 3. Onde fica cada responsabilidade

| Arquivo                                | Responsabilidade                                         |
| -------------------------------------- | -------------------------------------------------------- |
| `backend/app/bids/schemas.py`          | Validar entrada e definir respostas públicas             |
| `backend/app/bids/router.py`           | Receber HTTP, exigir papel e chamar o serviço            |
| `backend/app/bids/service.py`          | Aplicar regras e coordenar a transação                   |
| `backend/app/bids/signing.py`          | Criar representação canônica, hash e assinatura          |
| `frontend/src/components/BidPanel.tsx` | Formulário, feedback, liderança e histórico              |
| `backend/tests/test_bids_api.py`       | Verificar regras, rollback e concorrência com PostgreSQL |

Usamos POO por composição: `BidService` recebe uma `Session`. Não criamos uma hierarquia de classes porque ela não resolveria uma necessidade atual.

## 4. O caminho de um lance

1. FastAPI valida token, conta ativa, papel, UUID e valor em centavos inteiros positivos (até `10^12`). Campos extras são recusados.
2. O serviço bloqueia a linha do lote com `SELECT FOR UPDATE`.
3. Lê o líder atual e bloqueia as carteiras envolvidas, em ordem crescente de ID.
4. Depois dos locks, consulta o relógio do banco e revalida período, estado, líder, mínimo e saldo.
5. Confere a consistência do cabeçalho de assinatura e da reserva anterior.
6. Libera a reserva anterior, registra a liberação e cria o lance com assinatura.
7. Reserva o novo valor, registra o movimento e atualiza líder, versão e prazo.
8. Insere os eventos na outbox e executa **um commit**.
9. Só retorna HTTP 201 depois do commit.

Se ocorrer erro antes de confirmar, `rollback` desfaz todas as mudanças, inclusive a liberação anterior. Um teste provoca falha na gravação da outbox para verificar isso.

### Por que bloquear lote e carteira?

O lock do lote organiza duas pessoas disputando o mesmo objeto. O lock da carteira impede a mesma pessoa de comprometer o mesmo dinheiro em objetos diferentes. Sem o segundo lock, dois pedidos poderiam ler R$ 100 disponíveis e reservar R$ 80 cada.

A ordem é sempre **lote → carteiras ordenadas por ID**. A atualização usa os valores relidos sob lock, inclusive quando a sessão já tinha carregado a carteira.

Falhas do PostgreSQL que garantem uma transação abortada (`40P01`, deadlock, e `40001`, serialização) têm até três tentativas. Erros de conexão e resultados de commit desconhecidos não são repetidos automaticamente. Uma perda de resposta pode ocorrer depois de um aceite: consulte lote, histórico e carteira antes de reenviar. Ainda não há chave de idempotência para o endpoint de lance; a chave de depósitos continua existindo.

## 5. Onde entram os eventos?

O aceite grava `BidAccepted`. Se prorrogou, também grava `AuctionExtended`, com a mesma versão do lote. Os eventos contêm IDs públicos e dados da oferta, sem nome, e-mail ou saldo.

**Outbox é uma caixa de saída no banco.** O evento é salvo junto do lance; portanto não existe lance confirmado cujo evento se perdeu entre o commit e uma tentativa de envio pela rede.

Nesta entrega a caixa recebe eventos, mas ninguém os publica: `published_at` fica nulo. Na entrega 5 criaremos o consumidor e o WebSocket. Eles distribuirão fatos confirmados; não decidirão se há saldo. Fazer a reserva assincronamente permitiria aceitar uma oferta sem garantia financeira.

## 6. Contrato da API

### Oferecer lance

`POST /lots/{UUID_DO_LOTE}/bids`, com `Authorization: Bearer TOKEN_DO_LICITANTE`:

```json
{ "amount_cents": 8000 }
```

`8000` significa R$ 80,00. Não envie `80.00`, texto ou booleano.

HTTP 201 contém `id`, `lot_id`, `bidder_public_id`, `sequence`, `amount_cents`, `accepted_at`, `version`, `ends_at` e `extended`.

| Resposta | Exemplo de motivo                                                      |
| -------- | ---------------------------------------------------------------------- |
| 401      | Sem autenticação, token vencido ou conta inativa                       |
| 403      | Papel não permitido                                                    |
| 404      | UUID de lote inexistente                                               |
| 409      | Mínimo, saldo, líder, período, estado ou consistência impedem o aceite |
| 422      | Entrada inválida                                                       |
| 503      | Chave de assinatura não configurada                                    |

### Consultar histórico público

`GET /lots/{UUID_DO_LOTE}/bids?after=0`, sem login.

Retorna até 100 lances em ordem crescente de sequência. Para continuar, passe a última sequência em `after`. Cada registro contém somente ID do lance, identificador público aleatório do licitante, sequência, valor e horário. Nenhum nome, e-mail, ID privado ou saldo é exposto.

`GET /lots/{id}` também retorna `leaderPublicId` e `version`, para indicar liderança sem expor a conta privada.

## 7. Assinaturas: preparação para auditoria

Os campos de hash e assinatura já eram obrigatórios no modelo. Em vez de preencher valores falsos, esta entrega grava uma cadeia real: cada lance inclui o hash do anterior. A representação JSON tem chaves ordenadas, separadores fixos e horário UTC com microssegundos; o hash usa SHA-256. O hash e o cabeçalho são autenticados com HMAC-SHA256, usando `AUDIT_SECRET`, diferente da chave JWT.

Versão da chave: 1. `npm run setup:env` cria a chave local apenas se estiver vazia/ausente e preserva as já existentes. Não coloque segredos no Git e não troque a chave depois de ter lances assinados sem um plano de rotação. Faça backup privado dela junto aos demais segredos.

Para lotes anteriores sem lances, o cabeçalho é iniciado no primeiro aceite. Um lote com lances mas sem cabeçalho é recusado: não inventamos autenticidade retroativa para registros anteriores. A verificação atual confere o cabeçalho e sua ligação ao líder; ainda não percorre toda a cadeia em uma API pública.

**Isso não conclui a auditoria exigida.** Faltam verificador público completo, cabeçalho inicial na criação de cada lote e checkpoints externos. Ainda não declaramos proteção contra restauração de um histórico antigo nem contra acesso à chave de assinatura.

## 8. Como testar manualmente

```sh
npm run setup:env
npm run docker:up
npm run docker:seed
```

1. Abra http://localhost:5174 e entre como leiloeiro (`leiloeiro@example.com`, senha demo `DemoAuction2026!`).
2. Em Minha conta, importe uma obra; use início no passado e fim no futuro. Para testar prorrogação, deixe menos de dois minutos restantes.
3. Em dois navegadores/perfis diferentes, entre como `cliente1@example.com` e `cliente2@example.com`, mesma senha demo.
4. Cada cliente deposita R$ 100 simulados em Minha conta.
5. No primeiro cliente, abra o lote e ofereça R$ 80; o lote deve ter inicial compatível.
6. Consulte a carteira: total R$ 100, reservado R$ 80, disponível R$ 20.
7. No segundo cliente, atualize o lote e ofereça pelo menos o lance atual mais o incremento.
8. Atualize a página do primeiro cliente e consulte a carteira: a reserva desse lote deve ter sido liberada.
9. Tente valor baixo, saldo insuficiente, repetir como líder e ofertar antes/depois do período. Confira os motivos da recusa.

O botão **Atualizar lote** refaz a leitura. A interface não recebe alterações de outros clientes automaticamente nesta etapa. A contagem regressiva usa o relógio do navegador apenas para exibição; a decisão da API usa o banco. Ao prazo terminar, os lances param, mas o saldo vencedor permanece reservado até o futuro worker de liquidação. Use saldo fictício.

## 9. Testes automatizados

```sh
npm run db:up
TEST_DATABASE_URL=postgresql://auction:auction_dev@localhost:5433/auction_house \
  npm run check
npm run build
```

A fixture cria um schema PostgreSQL aleatório para cada teste e o remove ao terminar. Não apaga o schema de demonstração. Sem `TEST_DATABASE_URL`, os testes de integração são pulados; isso não valida concorrência.

Cobertura desta entrega: reserva/liberação, extrato, privacidade, mínimo, saldo, papel, período, formato do valor, prorrogação, assinatura reproduzível, rollback após liberação e duas disputas simultâneas (mesmo lote e mesma carteira em lotes diferentes). Frontend cobre recusa, envio em centavos, confirmação de liderança, login e resposta de rede incerta.

Não foi necessária migration: bids, reservations, entries, heads e outbox já existem na migration 0001. O próximo passo é publicar a outbox e atualizar as salas via WebSocket, com recuperação de estado na reconexão.

## Resultado da validação desta entrega

70 testes backend e dez frontend passaram. Também passaram lint, formatação, TypeScript e build de produção. Docker reconstruído: PostgreSQL, API e frontend saudáveis. `/ready`, frontend e `/api/ready` responderam HTTP 200; OpenAPI publicou GET/POST de lances. Reexecutar o setup preservou as chaves. Não foi feita inspeção visual no navegador, pois a ferramenta não disponibilizou navegador nesta sessão. Alterações locais, sem novo commit/push.

## Referências

- PostgreSQL 17, locks: https://www.postgresql.org/docs/17/explicit-locking.html
- SQLAlchemy, recarregar objetos já presentes na sessão: https://docs.sqlalchemy.org/en/20/orm/queryguide/api.html#populate-existing
