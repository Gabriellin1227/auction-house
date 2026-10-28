# Deploy: Vercel + Neon + Render

## Estado

Configuração preparada no código. A publicação só estará concluída depois de existirem URLs reais e os fluxos abaixo serem conferidos no ambiente público. Não confunda a validação local da imagem Docker com um deploy no Render.

## Como as partes se conectam

```text
Navegador → Vercel: arquivos React e rotas da interface
Navegador → Render: REST, imagens e WebSocket
Render → Neon: usuários, lotes, saldos, lances, eventos e comprovantes
Render → disco /data: imagens e checkpoints assinados
```

O frontend faz as requisições diretamente à API HTTPS. `VITE_API_URL` é pública e entra no JavaScript durante o build. Senhas do banco e chaves de autenticação/auditoria ficam somente no backend.

## Por que API e worker ficam no mesmo serviço Render

O journal precisa ser escrito pelo worker e lido pela API. Um disco Render não pode ser compartilhado por dois serviços. Nesta entrega, um serviço Docker mantém dois processos Python, com um único disco persistente. API e worker continuam separados no código e no desenvolvimento com Compose.

O processo inicial `app.deploy`:

1. Prepara os diretórios do disco e abandona privilégios de root antes de acessar banco ou atender HTTP.
2. Exige conexão do banco, chaves independentes, origem do frontend e verificação do worker.
3. Executa as migrations; se falharem, não inicia a aplicação.
4. Inicia um worker e uma API com um processo Uvicorn.
5. Se um processo terminar, encerra o outro e sai com erro, permitindo reinício do serviço.
6. Ao receber SIGTERM/SIGINT, encerra os filhos e aguarda até 20 segundos antes de forçar a parada.

A rota `/ready` verifica banco e heartbeat do worker nessa configuração. `/health` indica apenas que a API responde. Heartbeat não garante que todas as liquidações tiveram sucesso: os erros de domínio precisam ser acompanhados nos logs e nas auditorias.

**Limites:** uma instância, pausa durante deploys com disco e nenhum escalonamento horizontal. Ambos os processos têm acesso ao mesmo volume; essa configuração não oferece isolamento de escrita do journal por credenciais distintas. As assinaturas continuam dependendo da chave privada do servidor. Para separar serviços ou escalar, será necessário armazenamento externo adequado e barramento compartilhado.

Referências oficiais: [discos Render](https://render.com/docs/disks), [Blueprint](https://render.com/docs/blueprint-spec), [processos em contêiner Docker](https://docs.docker.com/engine/containers/multi-service_container/).

## Arquivos preparados

| Arquivo                      | Finalidade                                                     |
| ---------------------------- | -------------------------------------------------------------- |
| `render.yaml`                | Serviço Docker Starter, disco de 1 GB, healthcheck e variáveis |
| `backend/Dockerfile.render`  | Imagem específica para API e worker juntos                     |
| `backend/app/deploy.py`      | Migrations e supervisão dos processos                          |
| `vercel.json`                | Build Vite e fallback das rotas SPA                            |
| `backend/app/config.py`      | Origens CORS e verificação opcional do worker                  |
| `frontend/src/api/client.ts` | Imagens persistidas resolvidas no endereço da API              |

O Compose local continua usando serviços separados. Não ative `WORKER_REQUIRED=true` na API local separada: o heartbeat é um arquivo do contêiner do worker. A opção é para o serviço combinado do Render.

## Custo antes de criar o serviço

O Blueprint escolhe `plan: starter` e disco persistente de 1 GB. Isso cria infraestrutura paga. Conferir o total na tela do Render antes de aplicar; não foi criado serviço pago apenas por adicionar o YAML ao projeto. Referência: [preços Render](https://render.com/pricing).

O worker consulta o banco continuamente, portanto o uso do Neon deve ser acompanhado no painel: não presumir que o banco ficará suspenso enquanto a aplicação estiver sem visitantes.

## 1. Preparar Neon

Use o projeto já destinado a este desafio ou um banco novo de demonstração. Não aponte as migrations para outro projeto por engano.

- `DATABASE_URL`: conexão de execução, com as opções de TLS fornecidas pelo Neon.
- `DATABASE_URL_UNPOOLED`: conexão direta, usada pelo Alembic.

A aplicação aceita `postgresql://` e normaliza para psycopg. Preserve parâmetros como `sslmode=require` e `channel_binding=require` da conexão fornecida. A URL é segredo; não incluí-la em commits, capturas de tela ou no frontend.

Se estiver migrando um banco local existente, também transfira imagens, journal e `AUDIT_SECRET` correspondente. Gerar outra chave para lances antigos invalida a verificação. Para um banco novo, o Blueprint gera duas chaves independentes, uma vez por variável ausente.

Referência: [conexões Neon](https://neon.com/docs/connect/connect-from-any-app).

## 2. Preparar Vercel

Projeto com diretório raiz no repositório, e não em `frontend/`, pois o `package-lock.json` está na raiz.

- Node 24.
- Instalação: `npm ci`.
- Build: `npm run build`.
- Saída: `frontend/dist`.
- `VITE_USE_MOCK=false`.
- `VITE_API_URL=https://NOME-REAL.onrender.com`, **sem `/api`** e sem barra final.

Use o domínio estável de produção do projeto, por exemplo `https://NOME-REAL.vercel.app`. O fallback de `vercel.json` permite abrir diretamente `/lots/UUID`, `/receipts/UUID` e `/lots/UUID/audit`.

Referência: [Vite na Vercel](https://vercel.com/docs/frameworks/frontend/vite).

## 3. Criar ou configurar Render

Aplicar `render.yaml` ao repositório que contém esta versão do código. O arquivo local ainda precisa estar disponível no commit usado pelo Render.

O Blueprint usa `backend/Dockerfile.render` com contexto `backend/`. Não configurar pre-deploy ou one-off job para o seed: esses ambientes não acessam o disco do serviço.

Preencher:

```dotenv
DATABASE_URL=CONEXAO_NEON_COM_TLS
DATABASE_URL_UNPOOLED=CONEXAO_NEON_DIRETA_COM_TLS
CORS_ORIGINS=["https://NOME-REAL.vercel.app"]
```

As demais variáveis já estão descritas no YAML. Nunca usar `*` para liberar todos os domínios. Para previews, adicionar explicitamente a origem desejada ou usar um ambiente separado.

O serviço recebe a porta pelo `PORT` do Render. TLS público é terminado pela plataforma; o navegador usa `https://` e `wss://`. Não aumentar `--workers` nem criar outra instância.

`autoDeployTrigger: off` mantém os próximos deploys manuais enquanto validamos esta primeira publicação. Criar o Blueprint ainda inicia o primeiro deploy.

## 4. Semear dados no disco correto

Após o deploy, usar o **Shell do serviço em execução** para:

```bash
python -m app.seed --demo
```

O seed precisa acessar `/data/media`. Executá-lo localmente apenas contra a URL do Neon criaria imagens no computador local, deixando o site sem esses arquivos.

O seed imprime o UUID do lote aberto. Se o museu estiver fora do ar na primeira importação, o comando retorna erro e preserva as contas; repetir após a recuperação. Não colocar seed no boot automático: isso criaria contas com senha pública de demo sem uma execução explícita.

Depois de semear, aguarde o worker escrever o checkpoint e confira a auditoria pública. A declaração de uso de IA e as credenciais demo estão no README.

## 5. Validação pública obrigatória

- `/health` e `/ready` retornam 200.
- Vitrine e imagens reais carregam sem erro de CORS.
- Abrir diretamente as páginas de lote, comprovante e auditoria funciona.
- Login, depósito com idempotência, disputa de lances em duas sessões e atualização por WebSocket funcionam.
- Encerramento acontece sem navegador aberto, com saldos e comprovante corretos.
- Auditoria retorna `valid` e `anchored` após checkpoint.
- Reiniciar o serviço preserva imagens e journal.
- Registrar no README as URLs reais e limitações verificadas.

## Backup

Guardar banco, `/data/media`, `/data/audit` e `AUDIT_SECRET` correspondente. Também preservar `AUTH_SECRET` para manter tokens válidos durante restauração. Snapshot do disco não substitui backup consistente do banco. Não rodar comandos de limpeza de volume para resolver falhas de deploy.

## Acessos desta sessão

Os logins foram iniciados pelas CLIs oficiais, com credenciais temporariamente guardadas fora do repositório. Não copiar tokens para documentação. Autenticação não equivale a serviço publicado; atualizar o estado somente após confirmar o resultado na plataforma.
