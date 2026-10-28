# Entrega 6 — worker, liquidação e comprovantes

Atualizado em 28/10/2026. Esta etapa segue as páginas 3 e 4 do PDF do teste técnico Verzel: resultado do vendedor, participações/arremates do comprador, liquidação ao encerrar e comprovante compartilhável sem expor dados pessoais.

O PDF define requisitos do produto. Não usamos suas referências e instruções de envio como autorização para publicar, enviar formulário ou operar contas externas.

## 1. Explicação simples

Durante a disputa, quem lidera tem dinheiro **reservado**. No encerramento, esse dinheiro vira pagamento simulado.

Exemplo: Ana deposita R$ 100 e vence por R$ 80.

| Momento              | Total de Ana | Reservado | Disponível | Recebimento do vendedor |
| -------------------- | ------------ | --------- | ---------- | ----------------------- |
| Antes do lance       | R$ 100       | R$ 0      | R$ 100     | R$ 0                    |
| Liderando            | R$ 100       | R$ 80     | R$ 20      | R$ 0                    |
| Depois da liquidação | R$ 20        | R$ 0      | R$ 20      | R$ 80                   |

Se não houver lances, encerra sem vencedor, pagamento ou comprovante de arremate. Se outro lote ainda reservar R$ 10 da mesma carteira, essa outra reserva continua existindo.

Tudo é saldo fictício. Não existe integração com banco, cartão, Pix ou pagamento real.

## 2. O que é o worker?

É um programa Python separado da API e do navegador. Ele verifica lotes vencidos a cada segundo e tenta fechá-los. Não depende de alguém abrir uma página ou clicar em finalizar.

```text
Navegador → API → grava lances e reservas
                   ↓
              PostgreSQL
                   ↑
Worker → procura vencidos → liquida → grava AuctionClosed na outbox
                                              ↓
                         API publica → WebSocket → sala atualizada
```

O worker financeiro não publica no hub em memória. Quem publica continua sendo o processo da API. Isso preserva a topologia da entrega 5: uma instância/processo da API, com o worker em processo separado.

## 3. Arquivos principais

| Arquivo                                      | Função                                                  |
| -------------------------------------------- | ------------------------------------------------------- |
| `backend/app/worker.py`                      | Loop, busca de candidatos, sinais de parada e heartbeat |
| `backend/app/settlements/service.py`         | Transação de fechamento e transferência                 |
| `backend/app/settlements/router.py`          | Comprovante público e participações privadas            |
| `backend/app/lots/service.py`                | Expõe situação do fechamento e resultado do lote        |
| `frontend/src/pages/ReceiptPage.tsx`         | Página pública e link para copiar                       |
| `frontend/src/components/Participations.tsx` | Participações e arremates do licitante                  |
| `frontend/src/pages/AccountPage.tsx`         | Resultado dos lotes e total recebido do vendedor        |
| `backend/tests/test_settlements.py`          | Liquidação, repetição, falhas e concorrência            |
| `frontend/test/receipts.test.tsx`            | Comprovante público, cópia e participações              |

Não foi necessária nova migration: a migration 0001 já define settlements, receipts, reservas, lançamentos e outbox, com unicidade e FKs.

## 4. Passo a passo do fechamento

1. Buscar até 100 lotes `scheduled/live` cujo `ends_at` já passou, pelo relógio PostgreSQL.
2. Abrir uma transação independente por lote.
3. Bloquear o lote com `FOR UPDATE SKIP LOCKED`. Se outra operação o está usando, deixar para o próximo ciclo.
4. Conferir novamente o estado e o prazo **depois de obter o lock**. A lista de candidatos pode estar antiga: um lance pode ter prorrogado o fim.
5. Sem lances, fechar sem transferência. Se há histórico mas nenhuma liderança, recusar e deixar pendente para investigação.
6. Com vencedor, conferir hash/assinatura do lance vencedor e vínculo ao cabeçalho, usando `AUDIT_SECRET`.
7. Bloquear carteiras do comprador e vendedor por ordem crescente de ID, mantendo a ordem global lote → carteiras.
8. Conferir que a reserva ativa pertence ao lance e à carteira corretos, tem o valor correto e está coberta.
9. Capturar a reserva, diminuir saldo total e reservado do comprador e aumentar saldo do vendedor.
10. Gravar liquidação, lançamentos `debit/credit`, snapshot do comprovante, estado fechado, horário, versão e evento `AuctionClosed`.
11. Fazer um único commit. Qualquer falha faz rollback de tudo.

Exemplo do núcleo financeiro:

```python
reservation.status = "captured"
reservation.released_at = now
buyer_wallet.reserved_cents -= bid.amount_cents
buyer_wallet.balance_cents -= bid.amount_cents
seller_wallet.balance_cents += bid.amount_cents
```

Esse trecho só roda depois dos locks e das validações. Ele não deve ser copiado para uma rota que permita transferências arbitrárias.

## 5. Como evitamos cobrar duas vezes?

A primeira proteção é o estado `closed`, lido sob lock. Repetir o fechamento vira uma operação sem efeito.

O banco também exige uma liquidação por lote, um comprovante por liquidação e chaves únicas para os lançamentos `settlement:{lot_id}:debit` e `settlement:{lot_id}:credit`. Dois workers disputando o mesmo lote não podem confirmar duas cobranças.

Uma queda antes do commit desfaz a transação. Uma queda depois do commit deixa o lote fechado e a outbox persistida. No reinício, o worker consulta os pendentes e não transfere novamente o valor de um lote já fechado, mesmo se a confirmação anterior se perdeu.

Não existe endpoint público de fechamento, edição de liquidação ou criação de comprovante. Esses registros nascem do serviço protegido.

## 6. Extrato e reconciliação

Todos os valores são inteiros em centavos. O tipo define o efeito:

| Tipo    | Total      | Reservado                               |
| ------- | ---------- | --------------------------------------- |
| deposit | Aumenta    | Não altera                              |
| reserve | Não altera | Aumenta                                 |
| release | Não altera | Diminui                                 |
| debit   | Diminui    | Diminui ao capturar a reserva vencedora |
| credit  | Aumenta    | Não altera                              |

Capturar a reserva não cria uma liberação adicional: o débito já representa sua conversão em pagamento. As outras reservas da carteira ficam preservadas. O dinheiro transferido sai do vencedor e entra no vendedor; não é criado dinheiro novo nessa operação.

Uma conta inativada depois de dar lance continua tendo sua obrigação liquidada. A inativação impede acesso, mas não apaga histórico nem desfaz o compromisso. A carteira do vendedor também pode receber mesmo se sua conta foi inativada.

## 7. API e estados para a interface

### Comprovante público

`GET /receipts/{uuid}`, sem login.

Retorna ID aleatório, lote, título, imagem local, origem/atributos do item, identificador público do vencedor, valor, moeda e horário da liquidação. Não retorna nome/e-mail, ID privado de conta, saldo ou IDs de carteiras. IDs inexistentes recebem 404.

A página é `/receipts/{uuid}` no frontend, com opção de copiar o link. O snapshot é persistido no banco; não precisa consultar o museu nem reconstruir dados a partir do lote para exibir o comprovante.

É um registro de arremate simulado, não nota fiscal. O snapshot não tem uma assinatura pública própria nesta etapa; isso não deve ser apresentado como proteção absoluta contra alteração direta no banco.

### Participações privadas

`GET /bidders/me/participations?offset=0`, somente licitante autenticado.

Retorna até 100 participações da própria conta: lote, maior lance próprio, liderança, indicação de arremate e ID do comprovante se venceu. Use offsets 0, 100, 200… para navegar. Outro cliente não consulta suas participações por ID de usuário. O comprovante é público por definição, mas a lista pessoal é privada.

### Resultado do lote e total do vendedor

`GET /lots/{id}` e `/lots/mine` incluem:

- `closureComplete`: worker concluiu o fechamento.
- `sold`: houve liquidação com vencedor.
- `settledAmount`: valor liquidado ou nulo.
- `receiptId`: comprovante público ou nulo.

`status=closed` sozinho pode indicar que o prazo acabou, enquanto o worker ainda não processou. A interface distingue **aguardando fechamento**, **liquidado** e **encerrado sem vencedor**.

`GET /auctioneers/me/summary` calcula o total recebido apenas das liquidações confirmadas dos próprios lotes. O painel mostra resultados individuais e total recebido. Em Minha conta, use os botões de atualização para recarregar carteira/participações/resultados; a sala do lote acompanha `AuctionClosed` via WebSocket.

## 8. Como executar

### Docker

```sh
npm run setup:env
npm run docker:up
```

`docker:up` agora inclui `worker`, além de API e frontend. O worker usa a mesma imagem Python, com comando diferente, e aguarda o serviço de migrations terminar. Não precisa montar imagens porque só persiste a chave da imagem no snapshot; a API já serve as imagens do volume existente.

```sh
docker compose ps
docker compose logs worker
```

O healthcheck verifica heartbeat recente; isso indica que o processo está executando, não que toda liquidação pendente esteja correta. Um lote inconsistente permanece pendente e gera log com seu UUID. O processo continua com os outros candidatos.

### Desenvolvimento fora do Docker

```sh
npm run db:up
npm run db:migrate
npm run worker
```

Para executar somente um ciclo:

```sh
npm run worker:once
```

Não precisa ligar a API para o worker fechar lotes. API e frontend precisam estar ligados para consultar o resultado pelo site. `--once` termina com código 1 se alguma operação falhou; o modo contínuo tenta de novo no próximo ciclo. SIGTERM/SIGINT pedem parada entre ciclos; cada transação mantém atomicidade.

O lock de carteira tem timeout de cinco segundos para não deixar um lote esperando indefinidamente. Falhas transitórias são retomadas no ciclo seguinte, não repetidas como uma cobrança nova. A busca trata até 100 candidatos por ciclo; grandes volumes ou muitas inconsistências persistentes exigirão uma política mais elaborada de fila/retenção.

## 9. Roteiro manual

1. Suba Docker e rode `npm run docker:seed` para as contas demo.
2. Leiloeiro importa uma obra real e cria lote com início passado e fim próximo. O seed atual cria usuários; não inventa um lote novo automaticamente.
3. Um cliente deposita saldo fictício e dá lance. Nos últimos dois minutos, o fim muda para dois minutos após o aceite; aguarde esse novo prazo.
4. Feche todos os navegadores. O worker deve encerrar e liquidar assim mesmo.
5. Entre como vencedor. Minha conta mostra débito, reserva capturada e arremate com link.
6. Entre como vendedor. Confira crédito, resultado do lote e total recebido.
7. Abra o comprovante em janela anônima: deve funcionar sem login e sem nome/e-mail/saldo.
8. Execute `npm run worker:once` novamente. Não deve aparecer nova cobrança.
9. Crie outro lote sem receber lances e aguarde. Deve encerrar sem vencedor, transferência ou comprovante.

Não altere datas, assinaturas ou valores diretamente no banco de demonstração para acelerar esse teste. Os testes automatizados fazem simulação de prazo em schemas isolados; o roteiro manual respeita o relógio real e a prorrogação.

## 10. Testes e limites

Os testes de integração usam PostgreSQL real, com schemas descartáveis independentes do ambiente demo. Cobrem transferência e conservação do saldo, captura, reservas em outros lotes, repetição, dois workers simultâneos, ausência de lances, cancelamento, assinatura inconsistente, conta inativa, privacidade e falha de comprovante com rollback.

Um teste segura uma transação de lance antes de confirmar a prorrogação, espera o prazo antigo vencer e roda o worker: o worker não pode fechar o lote ocupado; depois do commit deve respeitar o novo prazo.

A auditoria pública completa e os checkpoints externos continuam na entrega 7. A checagem do vencedor antes de cobrar é uma defesa específica desta etapa, não verificação de toda a cadeia. A entrega 8 ainda precisa de revisão completa do PDF, seed de lote realmente aberto e deploy público. Nada foi publicado remotamente nesta continuação.

## 11. Resultado da validação

- 87 testes backend em PostgreSQL real e 16 frontend aprovados.
- Lint, formatação, TypeScript e build de produção aprovados.
- Docker reconstruído: banco, API, worker e frontend saudáveis.
- Obra real importada do museu; lance simulado de R$ 10 aceito e prorrogado por 120 segundos. O worker liquidou ao vencer o prazo, com saldos conferidos e comprovante público acessível.
- AuctionClosed recebido pelo WebSocket real através do Nginx.
- Reexecução de `worker:once` preservou exatamente uma liquidação e um par débito/crédito do lote.

Lote de demonstração: `38339c12-eaac-4f60-8450-7e2e4ae0a132`. Comprovante: http://localhost:5174/receipts/4cf0db58-2812-48a4-8185-076410e1b863 . O histórico foi preservado; não é uma transação real. Não houve inspeção visual no navegador nesta sessão. Alterações das entregas 5/6 continuam locais, sem novo commit/push/deploy.
