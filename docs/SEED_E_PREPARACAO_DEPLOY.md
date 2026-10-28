# Seed completo e preparação do deploy

## O que esta entrega resolve

O PDF pede um leiloeiro, dois clientes e pelo menos um lote realmente aberto. Agora o comando de seed prepara as três contas e importa uma obra real do Cleveland Museum of Art, com imagem local, dados persistidos e cabeçalho inicial assinado para a auditoria.

```bash
# Ambiente Docker
npm run setup:env
npm run docker:up
npm run docker:seed

# Desenvolvimento local, com banco e dependências já configurados
npm run db:migrate
npm run db:seed
```

A saída informa o UUID do lote criado ou reutilizado. Na interface Docker, abra `http://localhost:5174/lots/UUID`. O comando não exige que a API esteja rodando: usa o banco e o serviço de criação diretamente.

As contas são `leiloeiro@example.com`, `cliente1@example.com` e `cliente2@example.com`. Senha inicial pública: `DemoAuction2026!`. Contas já existentes mantêm senha, saldo e estado ativo. Os clientes começam sem saldo; faça um depósito simulado na carteira para testar os lances.

## Regras simples do seed

1. Cria somente as contas ausentes, com suas carteiras.
2. Confirma que o leiloeiro demo existe, está ativo e tem o papel correto.
3. Procura um lote desse leiloeiro, importado do Cleveland, já iniciado, não cancelado/encerrado e com mais de cinco minutos restantes.
4. Reutiliza esse lote se a imagem local existe e a auditoria é válida. Não precisa consultar o museu novamente.
5. Se não houver um lote nessas condições, importa a obra `94979`: abertura de R$ 10, incremento de R$ 1 e encerramento em 24 horas.

O prazo de cinco minutos evita entregar um lote prestes a acabar. O seed nunca prorroga um lote existente, apaga seu histórico ou altera seus lances. Lotes antigos continuam preservados. Se um lote elegível tiver auditoria inválida ou indisponível, o comando falha e pede revisão, sem reparar assinaturas automaticamente.

As contas são confirmadas em uma transação própria. Se a origem estiver indisponível na primeira importação, elas permanecem criadas, mas o comando termina com erro e sem inventar um lote. Corrija a disponibilidade e execute novamente.

## Por que duas execuções não criam dois lotes

Antes da busca, o seed obtém um advisory lock transacional do PostgreSQL. Outra execução do mesmo seed espera. A primeira cria e confirma o lote; a segunda então encontra e reutiliza o registro.

```python
session.execute(text("SELECT pg_advisory_xact_lock(20261028, 1)"))
# Buscar um lote aberto; se não existir, usar LotService.create(...).
# O commit da criação libera o lock depois de persistir o lote.
```

Esse lock serializa o comando de seed. As transações de lance continuam com seus próprios bloqueios e regras. O seed chama o mesmo `LotService` usado pela API: imagem, snapshot e cabeçalho de auditoria seguem o fluxo existente.

No Compose, o serviço `migrate` também monta `item_media`. Isso é necessário porque `docker:seed` usa esse serviço para executar o comando: sem o volume compartilhado, a imagem ficaria em um contêiner temporário e não seria encontrada pela API.

## Proxy após recriar a API

A verificação real encontrou um erro 502: ao recriar o contêiner da API, seu IP mudou e o Nginx continuou usando o endereço antigo. O upstream agora usa o DNS interno do Docker (`127.0.0.11`) com resolução periódica, para acompanhar essa mudança sem reiniciar o frontend. A configuração usa `resolve` e zona compartilhada, suportados pela imagem Nginx 1.28 utilizada no projeto. Referência: [upstream do Nginx](https://nginx.org/en/docs/http/ngx_http_upstream_module.html#resolve).

## Próxima entrega: publicação

**O site ainda não foi publicado.** Esta seção é um roteiro de preparação, não uma configuração de produção já validada.

| Parte                 | Destino previsto              | O que falta                                                                     |
| --------------------- | ----------------------------- | ------------------------------------------------------------------------------- |
| React/Vite            | Vercel                        | Projeto, URL da API, fallback das rotas SPA e teste de acesso direto às páginas |
| PostgreSQL            | Neon                          | Projeto, conexão TLS e aplicação das migrations                                 |
| API e WebSocket       | Host de contêiner persistente | Escolher host, domínio/HTTPS e manter um processo da API                        |
| Worker                | Mesmo host Docker da API      | Processo contínuo e acesso de escrita ao journal compartilhado                  |
| Imagens e checkpoints | Volumes persistentes no host  | Compartilhamento correto, backup e restauração testada                          |

Na arquitetura atual, Neon guarda os registros do banco; as imagens e o journal continuam em arquivos. Portanto, só configurar Vercel e Neon ainda não completa a publicação. Um servidor com Docker Compose é uma opção compatível com os volumes existentes. O `compose.yaml` atual é de desenvolvimento: usa PostgreSQL local e portas ligadas ao localhost; não deve ser apresentado como configuração de produção pronta.

### Adaptações de código antes de separar frontend e API

- Configurar CORS com a origem exata do frontend e os cabeçalhos usados por autenticação e depósitos.
- Resolver imagens de lotes e comprovantes na origem da API: hoje elas chegam como `/api/media/...`, usando o proxy local.
- Configurar a URL HTTPS da API no build e confirmar conexão `wss://` no navegador.
- Configurar o fallback da SPA para abrir diretamente páginas de lote, comprovante e auditoria.
- Criar configuração de produção com banco externo, secrets obrigatórios e volumes compartilhados. A API lê checkpoints; o worker escreve.

Não aumente réplicas nem processos da API enquanto o hub de eventos estiver em memória. O serviço atual pressupõe uma instância. Separar API e worker em hosts sem armazenamento compartilhado também quebra a leitura dos checkpoints.

### Banco Neon

Copie a conexão fornecida pelo painel e preserve as opções de TLS. As configurações existentes aceitam `postgresql://` e normalizam o driver para psycopg. `DATABASE_URL_UNPOOLED` está disponível para migrations. Para o seed, prefira a conexão direta nesta primeira publicação, evitando depender das particularidades de pooling enquanto validamos os locks.

Referência oficial: [conectar uma aplicação ao Neon](https://neon.com/docs/connect/connect-from-any-app).

### Vercel e WebSocket

A documentação atual da Vercel inclui suporte a WebSocket com FastAPI. A escolha de um host persistente neste roteiro decorre do worker contínuo, do hub local e dos arquivos compartilhados da aplicação atual. Migrar tudo para outra topologia exige rever esses componentes.

Referência oficial: [WebSockets na Vercel](https://vercel.com/docs/functions/websockets).

### Conferência antes de entregar a URL

1. Aplicar migrations e executar o seed no banco de demonstração.
2. Abrir um lote e sua imagem pelo endereço público.
3. Entrar como cada cliente, depositar saldo e disputar o mesmo lote em duas sessões.
4. Confirmar atualização sem recarregar, recusa clara de lance inválido e liberação da reserva anterior.
5. Confirmar encerramento, débito/crédito, comprovante público e auditoria com checkpoint.
6. Reiniciar API/worker e confirmar persistência de imagens, comprovantes e journal.
7. Registrar URLs reais, limitações e revisão humana no README.

## Validação automatizada desta entrega

Os testes de integração usam PostgreSQL e catálogo simulado, sem depender da internet: lote aberto com auditoria válida, reexecução sem origem, preservação de lote expirado, preservação de contas/saldos, falha da origem sem lote parcial, dois seeds concorrentes e recusa de cabeçalho ausente.

Validação desta continuação: **112 testes backend e 20 frontend aprovados**, lint, formatação, tipagem e build aprovados. Seed real executado duas vezes pelo Docker: criou e depois reutilizou o mesmo lote. Imagem JPEG respondeu HTTP 200, lote retornou `live` e auditoria `valid`/`anchored`. Proxy Nginx validado e acesso preservado após recriar a API. Banco, API, worker e frontend saudáveis. Sem commit, push ou deploy nesta etapa.
