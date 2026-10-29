# Conferência de deploy e entrega — 29/10/2026

## Estado atual

Aplicação publicada: [site](https://yorknew-auction-house.vercel.app), [Swagger](https://http--yorknew-api--fvlfd7l979w8.code.run/docs) e [repositório público](https://github.com/Gabriellin1227/auction-house). O ambiente usa Vercel, Neon e Northflank Free, com volume persistente gratuito. Não foi criado serviço pago do Render.

As evidências e limitações estão em [VALIDACAO_DEPLOY.md](VALIDACAO_DEPLOY.md). Implementação validada no commit `81d4f20`: 119 testes backend e 22 frontend aprovados; CI e imagem publicados com sucesso. `docs/` é versionado. Segredos continuam fora do Git/frontend.

## Infraestrutura concluída

- [x] Neon isolado, PostgreSQL 17, conexões TLS e migrations aplicadas.
- [x] Conta Northflank verificada manualmente; serviço Free de 512 MB.
- [x] Volume Free de 6 GB criado e anexado em `/data`.
- [x] API e worker saudáveis: `/ready` 200.
- [x] Seed remoto com três contas e lote aberto por 24 horas.
- [x] Vercel em produção, API real e mocks desabilitados.
- [x] Login pelo navegador, CORS e dois clientes WebSocket recebendo eventos.
- [x] Nova imagem iniciada; imagem JPEG preservada e auditoria válida/ancorada após reinício.

## Para fechar a entrega

Concluir as conferências públicas abaixo; revisar pessoalmente os fluxos e a declaração de uso de IA; confirmar prazo a partir do recebimento e enviar os links à Verzel. A submissão do formulário é uma ação do desenvolvedor.

## Roteiro obrigatório no endereço público

- [ ] Abrir vitrine; conferir ao vivo, agendados e encerrados; cancelados não aparecem.
- [ ] Abrir diretamente páginas de lote, comprovante e auditoria sem passar pela página inicial.
- [ ] Entrar como leiloeiro, administrar seus lotes e conferir impedimento de dar lance.
- [ ] Entrar em duas sessões como clientes diferentes e depositar saldo fictício.
- [ ] Disputar o mesmo lote: atualizar preço/histórico/liderança sem recarregar.
- [ ] Conferir primeiro lance, incremento mínimo, saldo insuficiente e impedimento de cobrir o próprio lance.
- [x] Conferir reserva do líder e liberação do cliente superado.
- [x] Conferir prorrogação por lance aceito nos últimos dois minutos.
- [x] Deixar o prazo vencer sem navegador aberto; confirmar liquidação única e saldos corretos.
- [x] Conferir encerramento sem lances, sem vencedor nem cobrança.
- [ ] Abrir participações/arremates, resultado do leiloeiro e comprovante compartilhável sem login.
- [x] Conferir auditoria pública e checkpoint; nenhuma informação pessoal privada exposta.
- [x] Reiniciar o serviço e conferir persistência de imagens e journal.
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
