# Entregas do Auction House

Atualizado em 28/10/2026. Este documento serve como mapa do projeto: o que cada entrega resolve, como conferir e o que ainda falta. A v1 é um marco de desenvolvimento, não a conclusão do desafio.

| Ordem | Entrega                          | Explicação simples                                       | Estado       |
| ----- | -------------------------------- | -------------------------------------------------------- | ------------ |
| 1     | Banco, migrations e Docker       | Criar as estruturas e guardar os dados entre reinícios   | Implementada |
| 2     | Contas, autenticação e papéis    | Saber quem entrou e o que pode fazer                     | Implementada |
| 3     | Catálogo externo e lotes         | Importar obras reais e administrar os próprios lotes     | Implementada |
| 4     | Depósitos e lances transacionais | Disputar sem comprometer o mesmo dinheiro duas vezes     | Implementada |
| 5     | Outbox, WebSocket e reconexão    | Avisar todas as salas quando a disputa muda              | Implementada |
| 6     | Worker, liquidação e comprovante | Encerrar sem navegador e transferir o saldo simulado     | Implementada |
| 7     | Auditoria e checkpoints          | Detectar adulteração e permitir verificação pública      | Implementada |
| 8     | Telas finais, deploy e entrega   | Conferir o PDF na aplicação pública e documentar limites | Pendente     |

## 1. Banco, migrations e Docker

PostgreSQL, SQLAlchemy e Alembic definem dez tabelas. Constraints e índices protegem integridade. Docker Compose sobe banco, migration, API e frontend, com healthchecks e volumes para banco, imagens e futuros checkpoints.

**Conferir:** `npm run db:up`, `npm run db:migrate`, `npm run db:check`. Reiniciar não deve apagar dados. `docker compose down -v` apaga volumes: não use para reiniciar normalmente.

## 2. Contas, autenticação e papéis

Cadastro, login JWT, senha Argon2, consulta/edição/inativação da própria conta. Existem leiloeiro e licitante. Cada um tem carteira; o backend confere usuário ativo, papel e propriedade. Seed explícito cria um leiloeiro e dois clientes sem redefinir contas existentes.

**Conferir:** `npm run docker:seed`, login no site e Swagger. Leiloeiro não pode depositar como licitante nem dar lances.

## 3. Catálogo externo e lotes

O painel busca obras CC0 no Cleveland Museum of Art e guarda título, atributos e imagem. O lote continua consultável se a API externa cair. Leiloeiro cria, consulta, edita lotes agendados sem lances e cancela sem lances. Vitrine e páginas individuais estão em português, com header persistente.

**Conferir:** importar uma obra real, criar lote e abrir sua URL. Outro leiloeiro não pode editá-lo. Cancelado não aparece na vitrine.

## 4. Depósitos e lances transacionais

Depósito fictício idempotente, saldo total/reservado/disponível e extrato privado. Lance aceita apenas licitante ativo, dentro do período, com valor mínimo e saldo. Lote e carteiras usam locks; reserva nova e liberação anterior acontecem juntas. O líder não cobre a própria oferta. Lance nos últimos 120 segundos redefine o fim para aceite + 120 segundos.

Outbox recebe `BidAccepted` e, quando necessário, `AuctionExtended`. Hashes/HMAC e cabeçalho já são gravados; isso prepara a auditoria, mas ainda não a conclui.

**Conferir:** dois clientes disputam o mesmo lote e verificam reservas. Testes exercitam também uma carteira em lotes distintos e rollback após falha de gravação.

**Limite:** após o prazo, o dinheiro do vencedor continua reservado até implementarmos a liquidação. Sem idempotência do lance: em resposta de rede incerta, consulte lote e carteira antes de reenviar.

## 5. Outbox, WebSocket e reconexão

A etapa lê eventos já confirmados e os distribui às salas. O navegador recupera o estado pelo HTTP na conexão/reconexão e ignora eventos antigos/repetidos por versão. Falhas de publicação têm retentativas. POO continua organizando os serviços; eventos comunicam os fatos confirmados.

**Conferir:** dois clientes atualizam preço, liderança, histórico e prazo sem recarregar; desligar/religar conexão recupera a situação atual. O protótipo usa uma única instância/processo da API; escalar exige distribuição entre processos. O publicador roda no lifespan, busca até 50 eventos a cada 0,5 segundo, registra falhas e retenta com espera exponencial. O navegador sincroniza por HTTP na reconexão e a cada 15 segundos. `published_at` confirma entrega ao hub, não a cada navegador.

## 6. Worker, liquidação e comprovante

Implementado o processo separado que encontra lotes vencidos e revalida o prazo sob lock. Com vencedor, captura reserva, debita comprador, credita leiloeiro e gera comprovante público com identificador aleatório. Guia: [WORKER_LIQUIDACAO_COMPROVANTES.md](WORKER_LIQUIDACAO_COMPROVANTES.md). Sem lances, encerra sem cobrança. Repetir execução não pode duplicar transferência.

**Conferir:** fechar mesmo com navegadores fechados; reiniciar worker e repetir sem duplicar liquidação. Painel do vendedor já mostra resultado/total recebido; licitante tem participações e arremates, com comprovante compartilhável.

## 7. Auditoria pública e checkpoints

Implementados o verificador completo da cadeia/assinaturas, o cabeçalho inicial para histórico vazio e os checkpoints em journal separado do banco. Guia: [AUDITORIA_PUBLICA_CHECKPOINTS.md](AUDITORIA_PUBLICA_CHECKPOINTS.md). Endpoint e tela públicos detectam alteração, inserção e remoção, inclusive do último lance. Rollback de banco/cabeçalho é comparado com o journal externo preservado. Nomes, e-mails e saldos ficam privados.

**Conferir:** testes de adulteração direta e rollback de histórico. Documentar limites: chave comprometida permite falsificação; volume separado não protege de um administrador que controla tudo.

## 8. Telas finais, deploy e entrega

Revisar todas as telas e fluxos do PDF. Seed de um lote realmente aberto implementado. Finalizar repositório público, deploy, README reproduzível e declaração de uso/revisão de IA. Vercel/Neon continuam como intenção; é necessário definir hospedagem da API persistente, WebSocket, worker e imagens antes de considerar o deploy concluído.

**Aceite:** percorrer o desafio pela URL pública, incluindo resultados, total recebido, participações, arremates, comprovante e auditoria. Nenhum deploy remoto foi executado até este marco.

## Como acompanhar

- [README](../README.md): instalação, comandos, regras e limites de execução.
- [EVENTOS_FASTAPI.md](EVENTOS_FASTAPI.md): guia local com exemplos e relação com REST/POO, movido para a pasta de documentação. A primeira versão está no histórico: `git show 9814237:EVENTOS_FASTAPI.md`.
- [STATUS_PROJETO.md](STATUS_PROJETO.md) e [LANCES_TRANSACIONAIS.md](LANCES_TRANSACIONAIS.md): guias locais detalhados; a pasta `docs/` está ignorada pelo Git.

As automações verificam Prettier, ESLint, TypeScript, Vitest, Ruff e pytest. A entrega 4 passou com 70 testes backend e dez frontend. A entrega 5 passou com 77 testes backend e 13 frontend, incluindo publicação, retentativa, isolamento de salas, duas conexões e reconexão. Para testar integração/locks de verdade, defina `TEST_DATABASE_URL`; sem ela os testes PostgreSQL são pulados.

## Validação atual (entrega 6)

87 testes backend e 16 frontend aprovados; lint, formatação, tipagem e build aprovados. Worker, API, banco e frontend saudáveis no Docker. Fluxo real local do museu ao comprovante, com prorrogação e saldos simulados conferidos. Testes de duas liquidações concorrentes e lance competindo com worker aprovados. Auditoria e checkpoints concluídos na entrega 7; próximo passo é finalizar seed aberto, deploy e revisão pública. Matriz de conferência: [MATRIZ_REQUISITOS_PDF.md](MATRIZ_REQUISITOS_PDF.md).

## Validação atual (entrega 7)

106 testes backend e 20 frontend aprovados; lint, formatação, TypeScript e build aprovados. No Docker, auditorias de um lote vazio e de um lote arrematado retornaram válidas e ancoradas pelo Nginx. As sete categorias principais usam imagens locais; o menu superior não tem mais Como funciona nem Todos os lotes. README reestruturado para instalação, uso, regras, auditoria, limites, pendências e declaração de IA. Nenhum deploy ou novo commit/push nesta continuação.

## Continuação: seed completo e roteiro de deploy

O seed agora garante um lote aberto por 24 horas ao importar uma obra real, ou reutiliza um lote demo elegível com imagem local e auditoria válida. Contas, saldos e históricos existentes são preservados. O requisito de seed deixou de ser pendência de implementação; o deploy público continua pendente. Detalhes, comandos, concorrência e adaptações de publicação estão em [SEED_E_PREPARACAO_DEPLOY.md](SEED_E_PREPARACAO_DEPLOY.md).

Validação desta continuação: **112 testes backend e 20 frontend aprovados**, lint, formatação, tipagem e build aprovados. Seed real executado duas vezes pelo Docker: criou e depois reutilizou o mesmo lote. Imagem JPEG respondeu HTTP 200, lote retornou `live` e auditoria `valid`/`anchored`. Proxy Nginx validado e acesso preservado após recriar a API. Banco, API, worker e frontend saudáveis. Sem commit, push ou deploy nesta etapa.

## Conferência de entrega em 28/10/2026

Última suíte: 118 testes backend e 22 frontend aprovados. Persistência da imagem e auditoria válida/ancorada confirmadas após reiniciar a imagem Render. Projeto Vercel criado, sem deploy; Neon e Render ainda sem autenticação confirmada. Último commit remoto continua 9814237; implementação atual ainda local. Checklist completa em [CHECKLIST_ENTREGA.md](CHECKLIST_ENTREGA.md).
