# Conferência de deploy e entrega — 28/10/2026

## Conclusão

A implementação principal está pronta para validação pública. A entrega ainda não está concluída: não existe deploy público desta aplicação, o código foi enviado no commit `40ced9e`, mas faltam acesso ao host gratuito e configurações de infraestrutura.

Esta conferência considera o código local, os logs dos testes, uma consulta real ao GitHub e à Vercel e as páginas 5 e 7 do PDF fornecido. Os requisitos funcionais detalhados estão mapeados em `MATRIZ_REQUISITOS_PDF.md`. Não representa nova inspeção visual completa nem teste em produção.

## Evidências já disponíveis

- [x] React, FastAPI e PostgreSQL, migrations e execução Docker.
- [x] CRUDs de contas/lotes, catálogo e imagens persistidos, carteira e depósito simulado.
- [x] Lances transacionais, reserva/liberação de saldo, prorrogação e atualização por WebSocket.
- [x] Worker de fechamento, liquidação, comprovantes públicos, participações e resultados.
- [x] Auditoria pública com cadeia assinada e checkpoints fora do banco, com limites documentados.
- [x] Seed: um leiloeiro, dois clientes e lote real aberto; reexecução preserva dados.
- [x] Última suíte: **118 testes backend e 22 frontend aprovados**, lint, formatação, tipagem e build.
- [x] Imagem específica do Render construída e executada localmente: migrations, API, worker e CORS.
- [x] Após parada do worker, o supervisor encerrou todo o serviço com erro; reinício preservou lote, JPEG e auditoria `valid`/`anchored`.
- [x] O erro anterior `Restart failed` no roteiro temporário foi investigado: o Docker mudou a porta publicada. A conferência pela porta atual retornou `/ready` 200. Não foi falha de inicialização da aplicação.
- [x] Repositório GitHub público confirmado: `Gabriellin1227/auction-house`.
- [x] Vercel autenticada e projeto `yorknew-auction-house` criado, ainda sem URL de produção.
- [x] Render autenticado e workspace consultável.
- [x] `docs/` incluído no versionamento; arquivos `.env` e credenciais continuam ignorados.

Não foi necessário repetir a suíte nesta conferência: nenhuma implementação foi alterada desde os logs acima. Foram atualizados somente os documentos.

## Ordem do que falta

| Ordem | Pendência                                    | Critério de conclusão                                                                                      |
| ----- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| 1     | Concluir autenticação do Neon                | CLI consegue listar o projeto destinado ao desafio e obter suas conexões com segurança                     |
| 2     | Concluir autenticação do Render              | Token efetivamente salvo e workspace consultável; clicar em autorizar não basta se a CLI perdeu a conexão  |
| 3     | Definir/criar o banco remoto                 | Projeto correto, conexão TLS de execução e conexão direta para migrations                                  |
| 4     | Aprovar o serviço pago descrito no Blueprint | Serviço Render com plano `starter` e disco de 1 GB autorizado antes de provisionar                         |
| 5     | Versionar a entrega atual                    | Revisar mudanças, commit e push; GitHub recebe código de eventos, liquidação, auditoria, seed e deploy     |
| 6     | Resolver publicação da documentação          | Resolvido nesta continuação: `docs/` incluído no versionamento, com instruções essenciais também no README |
| 7     | Publicar backend Render                      | Dockerfile correto, banco/chaves/origens configurados, migrations concluídas e `/ready` 200                |
| 8     | Publicar frontend Vercel                     | `VITE_USE_MOCK=false`, `VITE_API_URL` com URL real do Render sem `/api` e build público concluído          |
| 9     | Conferir CORS e WebSocket                    | Origem estável real da Vercel permitida; REST, imagens e `wss://` funcionam entre os domínios              |
| 10    | Executar seed no serviço remoto              | Shell do serviço com acesso ao disco; três contas e lote realmente aberto na URL pública                   |
| 11    | Percorrer o desafio no deploy                | Roteiro abaixo concluído com evidências e limitações registradas                                           |
| 12    | Finalizar README e envio                     | Links reais, credenciais demo, revisão humana e declaração de IA; depois preencher o formulário do PDF     |

### Estado do Git

Último commit da implementação completa enviado à branch `main`: `40ced9e` (`feat: prepara leiloes completos e infraestrutura de deploy`). O push executou os hooks e aprovou 118 testes backend e 22 frontend. A documentação também passou a acompanhar o repositório.

O repositório público já existe; não é necessário criar outro para separar frontend e backend. O projeto é um monorepo.

### Estado dos acessos

- **Vercel:** autenticada; projeto criado, nenhum deploy de produção.
- **Render:** autenticação concluída; token salvo e workspace `My Workspace` consultável. O serviço pago ainda não foi provisionado.
- **Neon:** autenticação concluída e projeto isolado `yorknew-auction-house` criado. Conexões privadas não devem ser publicadas.

Nenhum token, senha ou URL de conexão deve ser registrado neste arquivo.

## Roteiro obrigatório no endereço público

- [ ] Abrir vitrine; conferir ao vivo, agendados e encerrados; cancelados não aparecem.
- [ ] Abrir diretamente páginas de lote, comprovante e auditoria sem passar pela página inicial.
- [ ] Entrar como leiloeiro, administrar seus lotes e conferir impedimento de dar lance.
- [ ] Entrar em duas sessões como clientes diferentes e depositar saldo fictício.
- [ ] Disputar o mesmo lote: atualizar preço/histórico/liderança sem recarregar.
- [ ] Conferir primeiro lance, incremento mínimo, saldo insuficiente e impedimento de cobrir o próprio lance.
- [ ] Conferir reserva do líder e liberação do cliente superado.
- [ ] Conferir prorrogação por lance aceito nos últimos dois minutos.
- [ ] Deixar o prazo vencer sem navegador aberto; confirmar liquidação única e saldos corretos.
- [ ] Conferir encerramento sem lances, sem vencedor nem cobrança.
- [ ] Abrir participações/arremates, resultado do leiloeiro e comprovante compartilhável sem login.
- [ ] Conferir auditoria pública e checkpoint; nenhuma informação pessoal privada exposta.
- [ ] Reiniciar o serviço e conferir persistência de imagens e journal.
- [ ] Registrar data, URLs, resultados e limitações no README.

Testes de adulteração devem continuar no banco de teste isolado; não destruir o histórico da demonstração para testar a auditoria.

## Pontos de atenção no PDF

- Página 5: deixar **um lote com lances abertos na entrega**. O seed cria prazo de 24 horas; conferir novamente perto do envio e repetir o seed se necessário. Não alterar o prazo/histórico de um lote em disputa para esse fim.
- Página 5: prazo de sete dias corridos a partir do recebimento. A data de recebimento ainda não foi confirmada; não foi calculado um vencimento presumido.
- Página 7: link público da aplicação é obrigatório. Projeto criado na Vercel e testes locais não substituem esse link.
- Página 7: informar onde e como IA foi usada e o que foi revisado/ajustado pelo desenvolvedor. O texto atual do README reconhece que a revisão humana final continua pendente.
- Auditoria: manter explícitos os limites de HMAC, trechos sem checkpoint e controle conjunto de banco/journal; confirmar que essa interpretação atende à avaliação do desafio. Não prometer proteção absoluta contra administrador com todas as chaves.

Tema claro e cancelamento com estorno após lances são opcionais no PDF; não bloqueiam a entrega básica. Backups operacionais, rotação de chaves e revisão ampla de acessibilidade são melhorias registradas, sem tratá-las como novos requisitos obrigatórios do desafio.

## Guias

- [Deploy Vercel/Neon/Render](DEPLOY_VERCEL_NEON_RENDER.md)
- [Matriz dos requisitos do PDF](MATRIZ_REQUISITOS_PDF.md)
- [Seed e preparação do deploy](SEED_E_PREPARACAO_DEPLOY.md)
- [Auditoria e checkpoints](AUDITORIA_PUBLICA_CHECKPOINTS.md)

## Orçamento zero

A opção paga do Render foi recusada pelo desenvolvedor. Nenhum serviço pago foi criado. O roteiro ativo passou a ser [DEPLOY_GRATUITO.md](DEPLOY_GRATUITO.md): Vercel, Neon e Northflank Sandbox, sujeito à confirmação de volume persistente na franquia. Os passos antigos de provisionar Render são a alternativa paga, não ações aprovadas.

## Preparação concluída nesta continuação

Commit `40ced9e` publicado na main com 118 testes backend e 22 frontend aprovados. Neon autenticado, organização Free confirmada, banco isolado criado e migrations aplicadas sem diferenças de schema. Vercel vinculada. Conta Northflank Free conectada; verificação manual do cartão autorizada somente para o plano gratuito, sem autorização de cobrança. Volume persistente e deploy público ainda pendentes.

## Atualização: host gratuito preparado

Commit `d052fca` publicado; 119 testes backend e 22 frontend aprovados. CI remoto e publicação da imagem Docker concluíram com sucesso; pull anônimo da imagem confirmado. Banco Neon já migrado. Serviço Northflank preparado com 512 MB, volume gratuito de 6 GB e onze variáveis privadas conferidas. Não foi criado recurso pago. Bloqueio atual: concluir manualmente a verificação do cartão no Northflank para criar os recursos Free; ainda faltam publicação, seed no volume remoto e validação pública.
