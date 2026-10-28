# Entrega 2 — CRUD inicial, autenticação e carteira

## O que dá para testar

| Método e rota               | Função                                                                 | Acesso              |
| --------------------------- | ---------------------------------------------------------------------- | ------------------- |
| POST /users                 | Criar conta e carteira zerada, juntas                                  | Público             |
| POST /auth/token            | Fazer login e obter token                                              | Público, formulário |
| GET /users/me               | Consultar a própria conta                                              | Autenticado         |
| PATCH /users/me             | Alterar nome e/ou e-mail                                               | Autenticado         |
| DELETE /users/me            | Inativar a própria conta                                               | Autenticado         |
| GET /wallets/me             | Consultar total, reservado e disponível                                | Autenticado         |
| GET /auctioneers/me/summary | Consultar quantidade de lotes próprios e total recebido em liquidações | Somente leiloeiro   |

Esse CRUD é da própria conta: não há listagem pública de usuários nem acesso por ID de outra pessoa. DELETE mantém usuário, carteira e histórico no banco. Conta inativa não pode fazer login e seus tokens anteriores deixam de autorizar as rotas privadas.

Papéis: `bidder` (licitante, padrão do cadastro) ou `auctioneer` (leiloeiro). Papel não pode ser alterado no PATCH. Saldo, ativo, senha armazenada e identificadores também não são campos editáveis. PATCH aceita nome/e-mail, rejeita null, nome vazio e campos desconhecidos. E-mail é normalizado para minúsculas e sem espaços nas pontas.

Senhas possuem de 8 a 128 caracteres e são armazenadas com Argon2. O hash nunca é retornado. Erros de validação não repetem senha nem corpo do pedido. JWT usa chave privada do ambiente, expira em 30 minutos por padrão e não carrega nome, e-mail ou papel. O backend consulta usuário ativo e papel no banco a cada requisição autenticada.

Não adicionamos colunas: a migration 0001 já contempla essas entidades. Ainda não há recuperação/troca de senha, renovação de token, operações de depósito/lance ou CRUD de lotes. Esses fluxos não são simulados por rotas vazias.

## Iniciar

Na raiz do projeto:

```sh
npm run setup:env
npm run docker:up
npm run docker:seed
```

`setup:env` cria `.env` a partir do exemplo e gera AUTH_SECRET aleatória; não imprime a chave e não substitui chave já configurada. Execute antes de subir a API. O arquivo é ignorado pelo Git. Se editar uma chave existente, recrie o container da API para aplicar a mudança; os tokens antigos serão inválidos.

Também é possível rodar Python no host:

```sh
npm run setup:backend
npm run db:up
npm run db:migrate
npm run db:seed
node scripts/uv.mjs run --project backend --locked uvicorn app.main:app --app-dir backend --reload
```

Escolha API no Docker ou no host, sem disputar a mesma porta.

## Testar pelo Swagger

1. Abra http://localhost:8000/docs.
2. Use POST /users → Try it out → Execute para cadastrar uma conta, ou use o seed abaixo.
3. Clique Authorize no topo.
4. Em username, informe o e-mail; em password, a senha. Deixe client_id/client_secret vazios e authorize.
5. Execute GET /users/me e GET /wallets/me.
6. Execute PATCH /users/me para editar o perfil.
7. Se quiser testar DELETE, crie uma conta descartável; o endpoint a inativa.

### Usuários de demonstração

| E-mail                | Papel      | Senha            |
| --------------------- | ---------- | ---------------- |
| leiloeiro@example.com | auctioneer | DemoAuction2026! |
| cliente1@example.com  | bidder     | DemoAuction2026! |
| cliente2@example.com  | bidder     | DemoAuction2026! |

Seed explícito: somente usuários/carteiras nesta etapa, sem dinheiro fictício criado fora de uma movimentação. A integração externa adicionará o lote demonstrativo na próxima etapa. Todas as carteiras começam zeradas.

Rodar novamente preserva contas, senhas, ativo e saldos existentes. O seed não reativa conta inativada nem recupera senha alterada. O comando tem `--demo` explícito no script; as senhas são públicas para demonstração e não devem ser usadas em contas pessoais.

## Exemplos

Cadastro em POST /users:

```json
{
  "name": "Maria",
  "email": "maria@example.com",
  "password": "MinhaSenha2026!",
  "role": "bidder"
}
```

Edição em PATCH /users/me:

```json
{
  "name": "Maria Silva"
}
```

Login com curl (a senha a seguir é pública de demo):

```sh
curl -X POST http://localhost:8000/auth/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'username=cliente1@example.com' \
  --data-urlencode 'password=DemoAuction2026!'
```

A resposta tem access_token e token_type. Em outras ferramentas, envie `Authorization: Bearer SEU_TOKEN`. Não inclua tokens reais no Git.

## Respostas importantes

- 201: cadastro concluído.
- 200: consulta, edição ou login concluído.
- 204: conta inativada, sem corpo na resposta.
- 401: ausência de login, credencial incorreta, token inválido/expirado ou conta inativa.
- 403: papel não permitido.
- 409: e-mail já cadastrado.
- 422: formato inválido ou campo não permitido.
- 503 no login: AUTH_SECRET ausente; execute setup:env e recrie a API.

## Estrutura para continuar

```text
backend/app/
  auth/          # login, hashing, JWT e dependências de autorização
  users/         # schemas, repository, service e router
  wallets/       # leitura da carteira da conta autenticada
  auctioneers/   # consulta do resumo do próprio leiloeiro
  db/            # modelos e sessão SQLAlchemy
  seed.py        # usuários demo, idempotente e transacional
```

Rotas recebem/validam HTTP; UserService executa os casos de uso; UserRepository acessa persistência. Criação da conta e carteira é uma única transação. Integridade de e-mail permanece protegida pela UNIQUE do PostgreSQL, inclusive em concorrência.

## Verificação

```sh
npm run check
npm run db:test
```

A suíte de integração testa CRUD, hash de senha, carteira inicial, conflito de e-mail com rollback, acesso por papel/proprietário, entrada inválida, expiração/assinatura do token, inativação e seed idempotente. Sem TEST_DATABASE_URL, testes de integração ficam skipped no comando local; db:test e CI usam PostgreSQL real.

Referência: [tutorial oficial de segurança do FastAPI](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/).
