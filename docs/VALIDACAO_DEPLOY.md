# Deploy público — 29/10/2026

## Endereços

- Site: https://yorknew-auction-house.vercel.app
- API: https://http--yorknew-api--fvlfd7l979w8.code.run
- Swagger: https://http--yorknew-api--fvlfd7l979w8.code.run/docs
- Repositório: https://github.com/Gabriellin1227/auction-house

A Vercel entrega o React. O Northflank executa API e worker juntos em uma instância; o Neon guarda as transações PostgreSQL. O volume gratuito `yorknew-data`, 6 GB em `/data`, preserva imagens e checkpoints externos ao banco. API e worker usam o mesmo volume.

## Configuração e rastreabilidade

Northflank: projeto Default, região US Central, plano Free, `nf-compute-20` (0,2 vCPU / 512 MB), uma instância. Readiness HTTP `/ready` na porta 10000. Rollout `recreate`: atualizações interrompem brevemente o serviço e as conexões WebSocket; clientes reconectam e sincronizam o estado. Não há alta disponibilidade.

Imagem publicada pelo GitHub Actions, fixada na tag `sha-` do commit `81d4f20`. Esse commit define `HOME=/home/app` no Dockerfile: o processo sem privilégios não deve herdar `/root`, pois o libpq tenta consultar arquivos de certificado nesse diretório. TLS foi preservado. CI remoto e publicação da imagem passaram.

Variáveis privadas ficam no runtime do Northflank. A Vercel recebe somente `VITE_API_URL` público e `VITE_USE_MOCK=false`. CORS permite a origem estável da Vercel. Conexões Neon e chaves não fazem parte deste documento.

## Dados de demonstração

Senha pública: `DemoAuction2026!`.

| Papel     | E-mail                |
| --------- | --------------------- |
| Leiloeiro | leiloeiro@example.com |
| Licitante | cliente1@example.com  |
| Licitante | cliente2@example.com  |

Seed remoto criou as três contas e o lote aberto `fd14dd15-f103-4e75-82e6-9476b684fc44`, por 24 horas. Revalidar antes do envio. Executar o seed no contêiner, como usuário da aplicação e com o volume montado:

```sh
runuser -u app -- /app/.venv/bin/python -m app.seed --demo
```

O terminal administrativo do Northflank inicia como root; o comando acima evita arquivos de auditoria/imagens pertencentes a root. A reexecução preserva contas, saldos e lotes em disputa.

## Evidências observadas

- Site respondeu HTTP 200 sem autenticação da Vercel; login da conta cliente pelo navegador funcionou.
- API respondeu `/ready` 200 com banco e heartbeat do worker.
- Vitrine carregou lote real; catálogo externo retornou obras reais para o leiloeiro.
- Depósitos fictícios e dois lances sucessivos retornaram sucesso.
- Cliente superado ficou sem reserva; novo líder ficou com 1.100 centavos reservados.
- Lance no fim prorrogou o prazo; terceiro lance de 1.200 centavos foi transmitido como `BidAccepted` a dois clientes WebSocket independentes.
- Preflight CORS aceitou origem Vercel e cabeçalhos de autorização/idempotência.
- Hooks completos: 119 testes backend e 22 frontend, lint, formatação e tipagem aprovados. CI remoto também aprovado.

O lote `24785fa0-fa95-4abb-bf4d-2dccd89ffd19` foi criado para validar fechamento. Ele é separado do lote aberto do seed. Não apagar seu histórico financeiro para limpar a demonstração.

## Limites e conferências restantes

Liquidação pública confirmada após o rollout: lote de teste encerrado, `closureComplete=true`, valor de 1.200 centavos. Carteira do vencedor: 8.800 centavos; outro cliente: 10.000; leiloeiro: 1.200. Todas as reservas zeradas. Comprovante sem login: [9c44ace7-547e-4bd5-9b27-49f67d505bc0](https://yorknew-auction-house.vercel.app/receipts/9c44ace7-547e-4bd5-9b27-49f67d505bc0).

Auditoria retornou `integrity=valid`, `checkpoint_status=anchored` e três registros verificados. JPEG persistido respondeu HTTP 200 após a substituição do contêiner. Página direta do lote na Vercel carregou imagem e sala conectada. O lote aberto do seed foi preservado.

Neon Free tem cota mensal de compute; polling do worker mantém o banco ativo. Em 0,25 CU, 100 CU-h equivalem a cerca de 400 horas ativas. Não garante operação contínua por um mês inteiro. Northflank permanece Free; nenhum upgrade pago foi aplicado.

O desenvolvedor ainda precisa fazer sua revisão humana final, conferir o prazo contado do recebimento do desafio e enviar os links pelo formulário da Verzel. O deploy não envia esse formulário automaticamente.

## Conferências finais

O lote sem lances `0d8ef503-3059-4d3f-9551-f7678fdb4d39` encerrou com `closureComplete=true`, `sold=false` e sem comprovante/valor liquidado. Lance do leiloeiro retornou 403; abaixo do mínimo e sem saldo retornaram 409, sem aceitar lances no lote aberto do seed. O comprovante de R$ 12 abriu no navegador sem login.

A credencial `auction-deploy-temporario` foi revogada no Northflank após o provisionamento; o painel confirmou `Revoked`. O arquivo temporário da credencial foi removido.
