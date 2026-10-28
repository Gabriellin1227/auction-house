# Entregas do Auction House

Atualizado em 28/10/2026. Este documento serve como mapa do projeto: o que cada entrega resolve, como conferir e o que ainda falta. A v1 é um marco de desenvolvimento, não a conclusão do desafio.

| Ordem | Entrega                          | Explicação simples                                       | Estado       |
| ----- | -------------------------------- | -------------------------------------------------------- | ------------ |
| 1     | Banco, migrations e Docker       | Criar as estruturas e guardar os dados entre reinícios   | Implementada |
| 2     | Contas, autenticação e papéis    | Saber quem entrou e o que pode fazer                     | Implementada |
| 3     | Catálogo externo e lotes         | Importar obras reais e administrar os próprios lotes     | Implementada |
| 4     | Depósitos e lances transacionais | Disputar sem comprometer o mesmo dinheiro duas vezes     | Implementada |
| 5     | Outbox, WebSocket e reconexão    | Avisar todas as salas quando a disputa muda              | Próxima      |
| 6     | Worker, liquidação e comprovante | Encerrar sem navegador e transferir o saldo simulado     | Pendente     |
| 7     | Auditoria e checkpoints          | Detectar adulteração e permitir verificação pública      | Pendente     |
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

A próxima etapa lê eventos já confirmados e os distribui às salas. O navegador recupera o estado pelo HTTP na conexão/reconexão e ignora eventos antigos/repetidos por versão. Falhas de publicação têm retentativas. POO continua organizando os serviços; eventos comunicam os fatos confirmados.

**Conferir quando pronta:** dois clientes atualizam preço, liderança, histórico e prazo sem recarregar; desligar/religar conexão recupera a situação atual. O protótipo terá uma única instância/processo da API; escalar exige distribuição entre processos.

## 6. Worker, liquidação e comprovante

Ainda falta o processo que encontra lotes vencidos e revalida o prazo sob lock. Com vencedor, captura reserva, debita comprador, credita leiloeiro e gera comprovante público com identificador aleatório. Sem lances, encerra sem cobrança. Repetir execução não pode duplicar transferência.

**Aceite:** fechar mesmo com navegadores fechados; reiniciar worker e repetir sem duplicar liquidação. Atualizar painel do vendedor e arremates do comprador.

## 7. Auditoria pública e checkpoints

Ainda falta percorrer/verificar toda a cadeia e as assinaturas, autenticar histórico vazio e manter checkpoints fora do banco. Endpoint e tela públicos devem detectar alteração, inserção e remoção, inclusive do último lance. Nomes, e-mails e saldos ficam privados.

**Aceite:** testes de adulteração direta e rollback de histórico. Documentar limites: chave comprometida permite falsificação; volume separado não protege de um administrador que controla tudo.

## 8. Telas finais, deploy e entrega

Revisar todas as telas e fluxos do PDF. Preparar seed de um lote realmente aberto, repositório público, deploy, README reproduzível e declaração de uso/revisão de IA. Vercel/Neon continuam como intenção; é necessário definir hospedagem da API persistente, WebSocket, worker e imagens antes de considerar o deploy concluído.

**Aceite:** percorrer o desafio pela URL pública, incluindo resultados, total recebido, participações, arremates, comprovante e auditoria. Nenhum deploy remoto foi executado até este marco.

## Como acompanhar

- [README](README.md): instalação, comandos, regras e limites de execução.
- [Eventos em Python/FastAPI](EVENTOS_FASTAPI.md): exemplos e relação com REST/POO.
- `docs/STATUS_PROJETO.md` e `docs/LANCES_TRANSACIONAIS.md`: guias locais detalhados; a pasta `docs/` está ignorada pelo Git.

As automações verificam Prettier, ESLint, TypeScript, Vitest, Ruff e pytest. A entrega 4 passou com 70 testes backend e dez frontend. Para testar integração/locks de verdade, defina `TEST_DATABASE_URL`; sem ela os testes PostgreSQL são pulados.
