# Matriz de acompanhamento do PDF Verzel

Atualizado em 28/10/2026. Referência: `Teste tecnico Elite Dev - Verzel.pdf`, fornecido pelo usuário. Os estados abaixo distinguem funcionalidade local de entrega pública; testes aprovados não substituem percorrer a aplicação no deploy.

| Página | Requisito                                                                 | Situação atual                                                                                           | Onde conferir                                         |
| ------ | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| 2      | Itens provenientes de API pública                                         | Implementado: acervo Cleveland CC0, com snapshot e imagem persistidos                                    | Painel do leiloeiro, API de catálogo                  |
| 2      | Leiloeiro gerencia próprios lotes e não dá lances                         | Implementado, autorização no backend                                                                     | Rotas de lotes e testes de papéis/propriedade         |
| 2      | Licitante deposita, disputa e recebe comprovante                          | Implementado localmente com saldo fictício                                                               | Minha conta, sala e comprovante                       |
| 2 e 7  | Deploy público obrigatório                                                | Pendente                                                                                                 | Entrega 8                                             |
| 3      | Vitrine separa ao vivo/agendados/encerrados; oculta cancelados            | Implementado                                                                                             | Vitrine e filtros                                     |
| 3      | Painel mostra resultado e total recebido                                  | Implementado na entrega 6                                                                                | Minha conta do leiloeiro                              |
| 3      | Sala com preço, histórico, prazo e liderança sem recarregar               | Implementado via HTTP + WebSocket                                                                        | Entrega 5; topologia de uma instância/processo da API |
| 3      | Carteira com total, comprometido, disponível e depósito                   | Implementado                                                                                             | Minha conta; extrato privado                          |
| 3      | Participações e arremates com comprovante compartilhável                  | Implementado na entrega 6                                                                                | Minha conta do licitante; `/receipts/{id}`            |
| 3      | Auditoria pública sem login                                               | Implementado com estados de verificação/ancoragem                                                        | Auditoria pública, entrega 7                          |
| 3      | Motivos claros de recusa de lance                                         | Implementado                                                                                             | Mínimo, saldo, líder, período, papel e estado         |
| 4      | Itens continuam acessíveis quando a API externa cai                       | Implementado com persistência local                                                                      | Lote/imagem e snapshot do comprovante                 |
| 4      | Lances só no período; primeiro >= inicial; próximos >= atual + incremento | Implementado com relógio PostgreSQL                                                                      | `BidService` e testes transacionais                   |
| 4      | Líder não cobre próprio lance                                             | Implementado                                                                                             | API e formulário                                      |
| 4      | Reserva do líder e liberação ao ser superado                              | Implementado na mesma transação do aceite                                                                | Carteiras, reservas e extrato                         |
| 4      | Lance nos últimos dois minutos prorroga o fim                             | Implementado como aceite + 120 segundos; interpretação documentada                                       | Lances e outbox                                       |
| 4      | Ao encerrar, debitar vencedor e creditar leiloeiro                        | Implementado pelo worker separado                                                                        | Entrega 6, testes de concorrência e repetição         |
| 4      | Lote sem lances encerra sem vencedor                                      | Implementado sem cobrança ou comprovante de arremate                                                     | Worker e testes                                       |
| 4      | Detectar alteração, inserção e remoção no histórico                       | Implementado: verificação completa, cabeçalho assinado e journal externo; limites de ameaça documentados | Entrega 7                                             |
| 4      | Identificar licitante sem dados pessoais em auditoria/comprovante         | Comprovante, eventos e auditoria usam UUID público                                                       | Schemas públicos e testes de privacidade              |
| 5      | React, Python ou Node, banco persistente                                  | Implementado: React, FastAPI e PostgreSQL                                                                | Código, Docker e migrations                           |
| 5      | Seed: um leiloeiro, dois clientes e lote com lances abertos               | Implementado: três contas preservadas e lote real aberto, com imagem local e auditoria inicial           | Entrega 8                                             |
| 5      | README de configuração e limites                                          | Existente; revisão final pendente                                                                        | README e docs de cada entrega                         |
| 5      | Prazo de sete dias a partir do recebimento                                | Data de recebimento não confirmada; não inferir vencimento pela criação do PDF                           | Planejamento do usuário                               |
| 6      | Opcionais: busca, Compose, testes e temas                                 | Busca, Compose e testes presentes; tema claro e cancelamento com estorno não implementados               | Manter opcionais separados dos obrigatórios           |
| 7      | Repositório público, link público e declaração de IA/revisão              | Push da base anterior realizado; deploy e declaração final pendentes                                     | Entrega 8                                             |

## Decisões e limites atuais

- `closed` na apresentação pode significar prazo vencido; `closureComplete` confirma o processamento do worker. O frontend diferencia espera, liquidação e fechamento sem vencedor.
- Cancelamento com lances/estorno é opcional e continua fora desta versão. Sem lances, o cancelamento lógico está implementado.
- Saldo é simulado. Comprovante não é nota fiscal e não oferece pagamento real.
- O hub WebSocket exige uma instância/processo da API. Worker financeiro é separado; escala entre réplicas exige arquitetura adicional.
- A etapa 7 tem verificador público, cabeçalho vazio autenticado e checkpoints fora do banco. A proteção contra rollback depende de preservar o journal; o trecho ainda não ancorado fica pendente. Não cobre comprometimento da chave ou reescrita conjunta do banco/journal.
- Novos guias ficam em `docs/`. A pasta passou a acompanhar o versionamento nesta continuação da checklist de entrega.

Guias: [ENTREGAS.md](ENTREGAS.md), [WORKER_LIQUIDACAO_COMPROVANTES.md](WORKER_LIQUIDACAO_COMPROVANTES.md), [EVENTOS_FASTAPI.md](EVENTOS_FASTAPI.md) e [LANCES_TRANSACIONAIS.md](LANCES_TRANSACIONAIS.md).

## Continuação: seed completo e roteiro de deploy

O seed agora garante um lote aberto por 24 horas ao importar uma obra real, ou reutiliza um lote demo elegível com imagem local e auditoria válida. Contas, saldos e históricos existentes são preservados. O requisito de seed deixou de ser pendência de implementação; o deploy público continua pendente. Detalhes, comandos, concorrência e adaptações de publicação estão em [SEED_E_PREPARACAO_DEPLOY.md](SEED_E_PREPARACAO_DEPLOY.md).
