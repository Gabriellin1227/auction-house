# Yorknew — estado do projeto e continuação da v1

Atualizado em 28/10/2026. Este documento descreve código e validação reais; não significa conclusão do desafio.

## Marco v1

A base anterior foi preservada no commit local `0d10edd`, tag anotada `v1`, com versão npm 1.0.0. O documento histórico [VERSAO_V1.md](VERSAO_V1.md) está nesse marco. Nenhum push, release público ou deploy remoto foi executado.

Os CRUDs posteriores à tag foram registrados em `5649e45` e integrados à `main` local pelo merge `bb20f3b`. A entrega de lances foi registrada em `fda1e78`; guias iniciais em `9814237`. Ambos foram enviados à main remota por HTTPS. As entregas 5 (outbox/WebSocket), 6 (worker/liquidação/comprovante) e 7 (auditoria/checkpoints) estão implementadas no diretório de trabalho, sem novo commit/push. Para consultar o marco sem perder alterações, use `git show v1:VERSAO_V1.md`; não faça checkout/reset sobre o trabalho atual.

## Estado atual

| Área                  | Implementado                                                                                                                             | Ainda falta                                                      |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Usuários              | Cadastro, login JWT/Argon2, leitura/edição do próprio perfil e inativação                                                                | Recuperação de senha fora do escopo do PDF                       |
| Autorização           | Papel e usuário ativo verificados no backend; propriedade dos lotes                                                                      | Revisão final dos fluxos de liquidação                           |
| Catálogo externo      | Busca no acervo aberto do Cleveland Museum of Art; importação CC0                                                                        | Melhorias de filtros e tradução opcional dos metadados originais |
| Lotes                 | Criar, listar, detalhar, editar antes do início e sem lances, cancelar sem lances; listagem privada do proprietário                      | Revisão final no deploy público                                  |
| Persistência de itens | Título, atributos e imagem JPEG guardados localmente; consultas de lotes independentes da API externa                                    | Armazenamento compartilhado de produção e backup                 |
| Carteira              | Saldo, depósito simulado idempotente, extrato e reserva/liberação por lance                                                              | Backups e operação em produção                                   |
| Frontend              | Português, header persistente, URLs dos lotes, busca/categorias, Minha conta, lances, histórico, resultados, participações e comprovante | Revisão final de UX/acessibilidade no deploy                     |
| Banco                 | PostgreSQL, dez tabelas e Alembic 0001                                                                                                   | Migrations futuras quando o modelo evoluir                       |
| Eventos               | Produção transacional, publicador com retentativas e WebSocket                                                                           | Distribuição entre réplicas para escala futura                   |
| Auditoria/comprovante | Comprovante público, auditoria completa e journal de checkpoints externos                                                                | Backups, rotação de chaves e operação de produção                |
| Infra                 | Docker Compose, imagens, healthchecks, volumes, CI e hooks                                                                               | Vercel/Neon e definição do host do worker                        |

No catálogo real, as páginas separam lotes ao vivo, agendados e com prazo encerrado; cancelados não aparecem. “Prazo encerrado” é calculado pelo horário do servidor. `closureComplete` diferencia prazo vencido de fechamento efetivamente processado pelo worker.

Não existem CRUDs livres de lances, extrato, liquidação ou comprovantes. Esses registros devem nascer de operações protegidas, sem edição/exclusão que destrua o histórico.

## Como testar

```sh
npm run setup:env
npm run docker:up
npm run docker:seed
```

- Site: http://localhost:5174
- Swagger: http://localhost:8000/docs
- Desenvolvimento com Vite: `npm run dev`, porta 5173, API na porta 8000.
- `VITE_USE_MOCK=false` é o padrão atual; `true` é uma prévia explícita para desenvolvimento. Não há fallback silencioso para dados fictícios.
- Token em memória: recarregar a página exige login novamente.

Contas demo (senha pública `DemoAuction2026!`): leiloeiro@example.com; cliente1@example.com; cliente2@example.com. O seed não redefine senha, ativo ou saldo de contas existentes.

### Leiloeiro

Entre e abra Minha conta. Busque um item no acervo público, selecione-o, defina categoria, valores em reais e início/fim. Ao salvar, o backend consulta o item por ID e importa a imagem; não aceita URL arbitrária enviada pelo formulário. Se a importação falhar, não publica o lote.

É possível editar valores, categoria e horários somente antes do início e sem lances. Essa é uma decisão nova de escopo para o CRUD; após o início, valores/item ficam bloqueados. O cancelamento é lógico e preserva histórico; exige confirmação na interface e é recusado pelo backend quando há lances ou o prazo terminou.

### Licitante

Minha conta mostra perfil, total, comprometido, disponível e extrato. O depósito simulado recebe uma chave de idempotência: repetir o mesmo pedido não duplica o crédito; reutilizar a chave com valor diferente resulta em conflito. O saldo e o lançamento são atualizados na mesma transação com lock da carteira. Leiloeiros não usam o endpoint de depósito.

## Rotas novas

| Método | Rota                    | Acesso                                              |
| ------ | ----------------------- | --------------------------------------------------- |
| GET    | /categories             | Público                                             |
| GET    | /catalog/items?q=...    | Leiloeiro                                           |
| GET    | /lots                   | Público; filtros q, category, status e sort         |
| GET    | /lots/{id}              | Público; cancelado não é exposto                    |
| GET    | /lots/mine              | Leiloeiro, somente próprios                         |
| POST   | /lots                   | Leiloeiro                                           |
| PATCH  | /lots/{id}              | Proprietário, agendado e sem lances                 |
| DELETE | /lots/{id}              | Proprietário, sem lances; cancelamento lógico       |
| GET    | /stats                  | Público                                             |
| GET    | /wallets/me/entries     | Titular autenticado                                 |
| POST   | /wallets/me/deposits    | Licitante; cabeçalho Idempotency-Key UUID           |
| POST   | /lots/{id}/bids         | Licitante; valor inteiro em centavos                |
| GET    | /lots/{id}/bids?after=0 | Público; até 100 registros, paginação por sequência |
| GET    | /media/{arquivo}        | Imagens locais públicas                             |

Valores financeiros continuam em centavos inteiros no banco e API; o frontend exibe BRL. Contratos, nomes de campos e status de máquina permanecem em inglês. Textos da interface e feedbacks estão em português. Títulos/técnicas de obras importadas preservam o texto original do museu para não inventar metadados; a origem pode ser consultada na página do lote.

## UI/UX: fontes e cores

**Manter:** Cormorant Garamond em títulos/preços, Kumbh Sans na interface, marrom quase preto, ouro envelhecido e bordas discretas. A combinação comunica um salão privado de leilões e mantém a hierarquia visual.

**Ajustes aplicados:** corpo de peso 300 para 400; labels de 10–11px para pelo menos 12px; texto suave mais claro; avisos vermelhos mais claros; alvos de toque mobile de 48px; respeito à preferência de movimento reduzido. Tema claro e auditoria de acessibilidade completa continuam pendentes/opcionais conforme escopo.

Contraste calculado pela luminância relativa sRGB contra a superfície #14100D:

| Cor de texto              | Contraste |
| ------------------------- | --------- |
| Texto principal #F3ECE0   | 16,12:1   |
| Texto suave #A89C8A       | 7,02:1    |
| Dourado #D9A94B           | 8,77:1    |
| Vermelho anterior #C0392B | 3,48:1    |
| Vermelho novo #E5584B     | 5,25:1    |

WCAG AA pede 4,5:1 para texto comum. O vermelho anterior era inadequado para texto pequeno nessa superfície. Essas medições cobrem pares específicos de cores: não constituem certificação de acessibilidade, revisão visual completa de todos os dispositivos nem teste com usuários.

## Verificação e limites

Suíte atual: 112 testes de backend em PostgreSQL real e 20 de frontend; os testes frontend incluem navegação, login e página de carteira. Cobertura: CRUD com autorização/propriedade, snapshot consultável após falha externa, cancelamento protegido, depósito idempotente, extrato privado e 19 testes novos de lance (reservas, recusas, assinatura, prorrogação, rollback, concorrência e prazo revalidado após espera por lock). Build, tipagem, lint e formatação também são verificados.

Foi testada uma importação real do acervo público no ambiente Docker, com imagem acessível pelo volume local, além de depósito simulado repetido sem duplicação. O lote e o crédito são dados de demonstração locais, não transações reais. Backups e armazenamento remoto não foram configurados.

## Entrega 4: lance transacional

Guia detalhado: [LANCES_TRANSACIONAIS.md](LANCES_TRANSACIONAIS.md). A página de lote agora aceita lances, mostra liderança e histórico público. A reserva/liberação, a prorrogação e a produção de eventos usam uma única transação. `AUDIT_SECRET` separada é criada por `npm run setup:env`. A entrega 5 já distribui avisos por WebSocket e sincroniza a sala automaticamente; Atualizar lote permanece como opção manual. A entrega 6 captura a reserva e transfere o saldo ao vendedor automaticamente após o prazo. Sem lances, encerra sem cobrança.

Validação da entrega 4: 70 testes backend e dez frontend aprovados, lint/formatação/tipagem/build aprovados. Docker reconstruído com API, frontend e PostgreSQL saudáveis; rotas de lances confirmadas no OpenAPI e acesso à API pelo proxy do frontend verificado. `setup:env` repetido preservou as chaves. Não houve inspeção visual em navegador nesta entrega; nenhum navegador de automação estava disponível.

## Próxima entrega

1. Entrega atual: lance transacional, reserva/liberação, prorrogação e produção de eventos na outbox; guia em [LANCES_TRANSACIONAIS.md](LANCES_TRANSACIONAIS.md).
2. Entrega 5 implementada: publicador, WebSocket e recuperação na reconexão; detalhes em [EVENTOS_FASTAPI.md](EVENTOS_FASTAPI.md).
3. Entrega 6 implementada: worker separado, liquidação idempotente, resultados e comprovante compartilhável.
4. Entrega 7 implementada: auditoria pública, cabeçalho vazio assinado e checkpoints no volume separado.
5. Revisão final do PDF, deploy e README de entrega.

Referências: [acervo público Cleveland](https://www.clevelandart.org/open-access-api), [WCAG: contraste](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum).

Mapa das oito entregas: [ENTREGAS.md](ENTREGAS.md). A API usa um único processo/instância; o hub em memória não suporta escalonamento horizontal sem um barramento compartilhado.

## Validação da entrega 5

77 testes backend e 13 frontend passaram, incluindo duas conexões recebendo o mesmo aceite confirmado, retentativa com backoff, evento sem commit invisível, SKIP LOCKED, isolamento das salas, limites das filas e reconexão com recuperação de estado. Lint, formatação, tipagem e build aprovados. Docker reconstruído e saudável. O handshake WebSocket e o pedido inicial de sincronização foram confirmados tanto na API direta quanto pelo Nginx em localhost:5174. Nenhum deploy remoto foi feito. Entrega 5 permanece local, sem novo commit/push.

## Entrega 6 — fechamento e arremates

Guia: [WORKER_LIQUIDACAO_COMPROVANTES.md](WORKER_LIQUIDACAO_COMPROVANTES.md). Worker separado, ligado pelo Docker, encerra sem navegador, respeita prorrogação e liquida uma única vez. O vencedor tem débito e comprovante público; o leiloeiro recebe crédito e consulta resultado/total. Participações são privadas. A verificação do vencedor antes da cobrança não substitui a auditoria completa da etapa 7.

Conferência com o desafio: [MATRIZ_REQUISITOS_PDF.md](MATRIZ_REQUISITOS_PDF.md). Documentação concentrada em `docs/`; o arquivo ENTREGAS.md da raiz funciona como índice para o guia desta pasta.

## Validação da entrega 6

87 testes backend em PostgreSQL e 16 frontend aprovados; lint, formatação, tipagem e build aprovados. Docker com banco, API, worker e frontend saudáveis. Teste real local importou uma obra do museu, aceitou lance fictício de R$ 10, respeitou prorrogação de 120 segundos e liquidou automaticamente. Saldos comprador/vendedor conferidos; comprovante público consultado e AuctionClosed recebido pelo WebSocket via Nginx. Uma nova execução do worker manteve uma liquidação e apenas um débito/crédito.

Comprovante de demonstração local: http://localhost:5174/receipts/4cf0db58-2812-48a4-8185-076410e1b863 . Dados fictícios preservados para inspeção. Não houve inspeção visual em navegador, commit, push ou deploy nesta continuação. Auditoria pública e checkpoints são o próximo passo.

## Entrega 7 — auditoria pública e categorias

Guia: [AUDITORIA_PUBLICA_CHECKPOINTS.md](AUDITORIA_PUBLICA_CHECKPOINTS.md). Página pública `/lots/{id}/audit`, acessível por lote/comprovante. Verificação integral de cadeia, assinaturas, cabeçalho, liderança e checkpoints preservados; paginação só da exibição. Novos lotes recebem cabeçalho vazio assinado. Ausência/inconsistência não é reparada automaticamente.

Worker escreve journal JSONL no volume audit_checkpoints, API lê somente leitura. Resultado distingue ancorado, pendente, inválido e indisponível. Casos de modificação direta, remoção intermediária/final, inserção e rollback com cabeçalho antigo validamente assinado foram testados em schemas isolados. Limites sobre chave, administrador e journal apagado/truncado estão documentados.

Menu superior reduzido às sete categorias principais; imagens reais CC0 armazenadas localmente, com créditos no frontend. README reescrito conforme instalação, uso e limites do desafio, incluindo uso de IA e revisão humana final pendente.

Validação: 106 testes backend, 20 frontend, lint, formatação, tipagem e build aprovados. Docker saudável. Auditorias reais de lote vazio e arrematado retornaram válidas/ancoradas pelo proxy Nginx; sete imagens responderam como JPEGs locais. Bootstrap explícito aplicado somente ao lote legado conhecido vazio. Não houve adulteração do banco demo, inspeção visual completa no navegador, commit, push ou deploy nesta etapa. Próximo: seed reprodutível de lote aberto e deploy.

## Continuação: seed completo e roteiro de deploy

O seed agora garante um lote aberto por 24 horas ao importar uma obra real, ou reutiliza um lote demo elegível com imagem local e auditoria válida. Contas, saldos e históricos existentes são preservados. O requisito de seed deixou de ser pendência de implementação; o deploy público continua pendente. Detalhes, comandos, concorrência e adaptações de publicação estão em [SEED_E_PREPARACAO_DEPLOY.md](SEED_E_PREPARACAO_DEPLOY.md).

Validação desta continuação: **112 testes backend e 20 frontend aprovados**, lint, formatação, tipagem e build aprovados. Seed real executado duas vezes pelo Docker: criou e depois reutilizou o mesmo lote. Imagem JPEG respondeu HTTP 200, lote retornou `live` e auditoria `valid`/`anchored`. Proxy Nginx validado e acesso preservado após recriar a API. Banco, API, worker e frontend saudáveis. Sem commit, push ou deploy nesta etapa.

## Conferência de entrega em 28/10/2026

Última suíte: 118 testes backend e 22 frontend aprovados. Persistência da imagem e auditoria válida/ancorada confirmadas após reiniciar a imagem Render. Projeto Vercel criado, sem deploy; Neon e Render ainda sem autenticação confirmada. Último commit remoto continua 9814237; implementação atual ainda local. Checklist completa em [CHECKLIST_ENTREGA.md](CHECKLIST_ENTREGA.md).

## Publicação: progresso atual

Código completo enviado na main no commit `40ced9e`; `docs/` está versionado. Vercel vinculada, Neon autenticado em organização Free, banco isolado criado e migrations aplicadas sem diferenças de schema. Opção paga Render recusada; alternativa Northflank Free em preparação. A conta Northflank está conectada e exige verificação manual de cartão, autorizada apenas para o gratuito. Nenhuma URL pública foi entregue e nenhum serviço pago foi criado. Roteiro ativo: [DEPLOY_GRATUITO.md](DEPLOY_GRATUITO.md).
