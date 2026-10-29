# Publicação com orçamento zero

## Decisão do projeto

O desenvolvedor escolheu uma alternativa gratuita ao serviço pago do Render. Nenhum serviço pago foi criado. O Blueprint `render.yaml` continua como exemplo da alternativa paga e **não deve ser aplicado no roteiro gratuito**.

O destino pretendido é:

| Parte             | Serviço                       | Estado                                                                                                           |
| ----------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Interface React   | Vercel                        | Autenticada, projeto vinculado; sem deploy público                                                               |
| PostgreSQL        | Neon                          | Autenticado; projeto isolado `yorknew-auction-house` criado em AWS us-east-1, PostgreSQL 17 e compute de 0,25 CU |
| API + worker      | Northflank Sandbox            | Conta Free conectada; verificação manual do cartão e confirmação do volume pendentes                             |
| Imagens + journal | Volume persistente do serviço | Opção gratuita de 6 GB confirmada no formulário; criação depende da verificação da conta                         |

Essa tabela registra preparação; não significa que o site está publicado.

## Por que não basta selecionar Render Free

O serviço gratuito do Render suspende após inatividade e não permite disco persistente. O projeto precisa de arquivos preservados e fechamento dos leilões sem depender de visitas ao site. Remover o disco e manter tudo em arquivos temporários perderia imagens e checkpoints em reinícios; deixar o worker suspenso adiaria os fechamentos.

Referência: [limites do Render Free](https://render.com/docs/free).

## Alternativa a confirmar no Northflank

O plano Sandbox anunciado inclui dois serviços, dois jobs, um banco/addon, serviços sem suspensão e franquia de até US$ 20 mensais em recursos, sem cartão. A disponibilidade efetiva e as cotas devem ser conferidas na conta. Não fazer upgrade para um plano pago ou cadastrar cartão para completar este roteiro.

O primeiro objetivo é usar **um serviço combinado** com API e worker, uma instância e volume de 6 GB. O Dockerfile `backend/Dockerfile.render` é reaproveitável: o nome foi escolhido para o primeiro destino, mas o comando `python -m app.deploy` não depende da API do Render. Ele usa PostgreSQL externo, variáveis de ambiente e o diretório persistente `/data`.

Referências: [preços Northflank](https://northflank.com/pricing), [plano Sandbox](https://northflank.com/docs/v1/application/billing/pricing-on-northflank), [volumes](https://northflank.com/docs/v1/application/databases-and-persistence/add-a-volume).

### Limite importante

Uma franquia gratuita não significa recursos ilimitados ou um contrato de disponibilidade de produção. Se a conta exigir cobrança para montar o volume, não publicar com armazenamento temporário silenciosamente: interromper o provisionamento e escolher armazenamento durável compatível ou outro host gratuito.

## Configuração preparada

- Repositório: `https://github.com/Gabriellin1227/auction-house`.
- Branch: `main`, código completo enviado no commit `40ced9e`.
- Dockerfile: `backend/Dockerfile.render`.
- Contexto do build: `backend/`.
- Porta HTTP: 10000; configurar `PORT=10000`.
- Healthcheck: `GET /ready`.
- Instâncias: uma.
- Volume: 6 GB, montado em `/data` (opção permitida no projeto gratuito).
- Execução: `python -m app.deploy`, já definido na imagem.

Variáveis privadas do serviço:

```dotenv
DATABASE_URL=CONEXAO_NEON_COM_TLS
DATABASE_URL_UNPOOLED=CONEXAO_NEON_DIRETA_COM_TLS
AUTH_SECRET=CHAVE_ALEATORIA_PRIVADA
AUDIT_SECRET=OUTRA_CHAVE_ALEATORIA_PRIVADA
CORS_ORIGINS=["https://DOMINIO-REAL-DA-VERCEL"]
MEDIA_DIR=/data/media
AUDIT_DIR=/data/audit
WORKER_REQUIRED=true
EVENTS_ENABLED=true
PORT=10000
```

As conexões/chaves reais não ficam neste documento. Para o banco novo, gerar chaves novas. Se transferir histórico existente, é obrigatório preservar a chave de auditoria correspondente, as imagens e o journal.

Após o backend estar acessível por HTTPS, configurar na Vercel:

```dotenv
VITE_USE_MOCK=false
VITE_API_URL=https://DOMINIO-REAL-DA-API
```

A URL da API não termina com `/api`. Confirmar o domínio estável real da Vercel antes de configurar CORS.

## Cotas do Neon

As migrations já foram aplicadas no projeto Neon e `alembic check` não encontrou diferenças com os modelos. Conexões com TLS e chaves novas estão preparadas em diretório privado fora do Git.

O anúncio atual do plano gratuito informa 100 CU-h por projeto por mês. Em 0,25 CU, isso equivale a até 400 horas de atividade, aproximadamente 16 dias contínuos. O worker consulta o banco continuamente e tende a mantê-lo ativo; portanto, essa configuração não garante um mês inteiro de operação contínua no gratuito. Acompanhar o consumo e não habilitar cobrança automática para resolver o esgotamento.

A demonstração de sete dias exige cerca de 42 CU-h somente para o compute mínimo, antes de considerar outras atividades. O prazo real de entrega ainda depende da data em que o desafio foi recebido.

Referência: [franquia atual do Neon Free](https://neon.com/blog/neon-free-plan-1-gb-per-project).

## Sequência restante

1. Concluir cadastro/login no Northflank Sandbox, sem plano pago.
2. Conferir cota de serviço, memória e volume persistente na conta.
3. Aplicar migrations no banco isolado e configurar os secrets do backend.
4. Construir e publicar o backend; conferir `/ready` e logs de ambos os processos.
5. Publicar frontend na Vercel com a URL real da API e validar CORS/WebSocket.
6. Rodar `python -m app.seed --demo` no contêiner em execução, com acesso ao volume.
7. Percorrer a [checklist de entrega](CHECKLIST_ENTREGA.md) na URL pública.
8. Atualizar README e documentação com as URLs reais e os limites efetivamente verificados.

O repositório público está atualizado. A autenticação do Northflank é a próxima dependência externa; a interface ficou em `Connecting` no navegador integrado durante a preparação.

## Verificação observada na conta

O painel confirmou `Team Free`, mas mostrou `Payment method required` mesmo para um serviço que informa não cobrar. Isso contradiz a indicação de cadastro sem cartão da página pública de preços para esta conta. O desenvolvedor autorizou verificar manualmente a conta gratuita; não autorizou serviço ou volume pago.

O cadastro/login no Northflank está concluído. Permanecem a verificação manual do cartão, a conexão do repositório e a confirmação de volume dentro da franquia. Não usar a alternativa Render paga para contornar esse bloqueio. O banco remoto já está migrado; ainda não houve publicação da aplicação nem seed remoto.

## Imagem para deploy sem integração GitHub no host

O workflow `.github/workflows/publish-api.yml` constrói `backend/Dockerfile.render` e publica a imagem no GitHub Container Registry usando somente o `GITHUB_TOKEN` temporário do job. Não inclui banco, senha, `.env` ou chave de auditoria na imagem. As tags são `latest` e `sha-COMMIT_COMPLETO`.

Destino: `ghcr.io/gabriellin1227/auction-house-api`. Antes de usá-la como imagem pública no Northflank, conferir a conclusão do workflow, a visibilidade do pacote e um pull anônimo. A publicação do pacote não equivale a site publicado.

No Northflank, a modalidade **Deployment** executa a imagem pronta. Isso evita depender do vínculo GitHub App/time, que ainda não estava aparecendo como associado mesmo com o aplicativo já instalado na conta. Não foi necessário alterar as permissões existentes do GitHub App.

## Estado confirmado do serviço preparado

- Serviço `yorknew-api`, projeto `Default`, região US - Central.
- Fonte GitHub `Gabriellin1227/auction-house`, branch `main`; vínculo agora disponível no formulário.
- Contexto `/backend`, Dockerfile `/backend/Dockerfile.render`, validado pelo painel.
- Plano gratuito `nf-compute-20`: 0,2 vCPU compartilhada, 512 MB, uma instância.
- Porta pública HTTP 10000, healthcheck `/ready`, intervalo de 10 s e timeout de 5 s.
- Onze variáveis de execução preenchidas e comparadas com a configuração privada; nenhum segredo incluído no build/frontend/Git.
- Volume `yorknew-data`, `/data`, 6 GB: o painel informa que não será cobrado neste projeto Free.
- Cadastro de cartão ainda precisa ser concluído manualmente pelo desenvolvedor. O painel continua informando falta de pagamento padrão verificado. A tentativa de criação do volume parou na validação de nome/país do formulário de pagamento; nenhum volume nem serviço foi criado.

A imagem também está publicada e disponível sem autenticação em `ghcr.io/gabriellin1227/auction-house-api:latest`. Workflow de publicação e CI do commit `d052fca` concluíram com sucesso. A modalidade Combined (Git + build) já está preparada no Northflank; a imagem pronta permanece como alternativa de deploy e rastreabilidade.

## Correções encontradas pelos hooks

O teste de navegação deixou de esperar o atraso artificial do catálogo fictício; os dados e as regras da interface continuam os mesmos. O encerramento de WebSocket agora libera a inscrição na sala antes de aguardar tarefas canceladas e protege essa espera contra cancelamento externo. Um teste de cancelamento repetido comprova que a capacidade da sala é liberada mesmo durante a parada forçada.

Última validação completa: **119 testes backend e 22 frontend aprovados**. Código no commit `d052fca`, enviado à main sem pular hooks. Não existe URL pública da aplicação até concluir a criação do host, volume e frontend.
