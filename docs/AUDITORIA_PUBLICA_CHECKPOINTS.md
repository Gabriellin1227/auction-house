# Entrega 7 — auditoria pública e checkpoints

Atualizado em 28/10/2026. Requisitos de referência: páginas 2–4 do PDF Verzel, especialmente histórico auditável sem login, detecção de alteração/inserção/remoção e identificação de licitantes sem dados pessoais.

## 1. A ideia simples

Cada lance guarda uma impressão digital (hash) de seus dados e do hash anterior. Uma assinatura autenticada impede que alguém que só altera o banco simplesmente recalcule os hashes e esconda a mudança.

O cabeçalho assinado registra quantos lances existem e o hash final. Isso permite detectar a remoção do último lance, que uma cadeia sozinha não detectaria.

Ainda existe um problema: restaurar **histórico e cabeçalho juntos** de um backup antigo preserva assinaturas antigas válidas. Por isso o worker escreve checkpoints em outro volume. Se o banco voltar para trás, mas o journal continuar preservado, a auditoria encontra a divergência.

## 2. O que está implementado

- Página pública `/lots/{uuid}/audit`, com acesso a partir do lote e do comprovante.
- API pública `GET /lots/{uuid}/audit?after=0`.
- Verificação da sequência inteira, vínculos dos hashes, dados canônicos, HMAC de cada lance, cabeçalho e liderança.
- Histórico vazio exige cabeçalho inicial assinado. Ausência de cabeçalho é falha, não uma lista vazia válida.
- Checkpoints autenticados e encadeados em arquivos JSONL fora do PostgreSQL.
- Journal escrito pelo worker; API lê o volume em modo somente leitura no Docker.
- Novos lances e liquidações recusados se a auditoria encontrar inconsistência. Armazenamento indisponível também impede classificá-la como válida.
- Bootstrap explícito de cabeçalhos vazios para lotes legados sem lances; nunca recria assinaturas de lances antigos.

Os registros públicos usam apenas UUID público do licitante. Não incluem nome, e-mail, saldo, carteira ou ID privado de conta.

## 3. Dados assinados

A representação canônica do lance contém:

```python
{
    "lot_id": "uuid-do-lote",
    "bid_id": "uuid-do-lance",
    "sequence": 1,
    "bidder_public_id": "uuid-publico-do-licitante",
    "amount_cents": 8000,
    "accepted_at": "horario UTC com microssegundos",
    "previous_hash": "hash-do-anterior",
    "key_version": 1,
}
```

JSON com chaves ordenadas e separadores fixos gera bytes determinísticos. O primeiro hash anterior é 64 zeros. O código usa SHA-256 para o registro e HMAC-SHA256 com `AUDIT_SECRET` para autenticar o hash e o cabeçalho. Há separação de domínio entre assinatura de lance, cabeçalho e checkpoint.

HMAC é uma autenticação com segredo compartilhado entre API e worker. Não é assinatura digital de chave pública nem verificação independente no navegador: a verificação pública é realizada pelo endpoint do servidor. Nunca publique a chave para permitir que o navegador a recalcule.

## 4. Como a auditoria verifica

1. Lê e verifica o journal externo, antes de iniciar o snapshot de dados do PostgreSQL.
2. Consulta lote, cabeçalho e lances em uma transação `REPEATABLE READ` na rota pública.
3. Confere sequências 1, 2, 3… sem lacunas, ordem, hash anterior, hash recalculado e assinatura.
4. Confere quantidade e último hash contra o cabeçalho assinado.
5. Confere se a liderança aponta para o último lance.
6. Compara cada checkpoint preservado com o hash correspondente no banco. Um checkpoint com sequência maior que o histórico atual denuncia possível remoção/rollback.
7. Retorna resultado e até 100 registros públicos para exibição.

A paginação limita só a resposta: a cadeia inteira é examinada a cada consulta, inclusive se `after` pede uma página adiante.

**Por que ler o journal antes do snapshot?** Se um lance e seu checkpoint forem confirmados durante a consulta, não devemos comparar um checkpoint novo com uma fotografia antiga do banco e acusar falsamente rollback. A ordem escolhida permite que o resultado seja momentaneamente pendente, preservando a consistência da verificação.

Durante lance e liquidação, o serviço já mantém o lock do lote, que impede os escritores normais de mudar sua cadeia enquanto ela é conferida. A leitura pública não mantém esse lock durante a varredura.

## 5. Estados da API e da tela

| Campo/estado                    | Significado                                                    |
| ------------------------------- | -------------------------------------------------------------- |
| `integrity=valid`               | Cadeia/cabeçalho atuais passaram nas verificações              |
| `integrity=invalid`             | Há inconsistência no histórico, cabeçalho ou journal           |
| `integrity=unavailable`         | Não foi possível consultar o armazenamento de checkpoints      |
| `checkpoint_status=anchored`    | O último hash atual corresponde ao maior checkpoint preservado |
| `checkpoint_status=pending`     | Falta ancorar o estado atual, ou nenhum journal foi encontrado |
| `checkpoint_status=invalid`     | Journal ou vínculo ao banco inconsistente                      |
| `checkpoint_status=unavailable` | Armazenamento inacessível                                      |

Só exibimos **Histórico íntegro e ancorado** quando a cadeia é válida e o checkpoint está ancorado. Cadeia válida com checkpoint pendente recebe aviso separado. Falhas não são convertidas em sucesso nem escondidas como histórico vazio.

A resposta também contém `verified_count`, `checkpoint_sequence`, `head_sequence`, `last_hash`, `issues`, `history` e `next_after`. A rota usa `Cache-Control: no-store`. A tela oferece Verificar novamente; ela representa uma consulta naquele momento, não monitoramento contínuo.

Lotes cancelados continuam auditáveis por UUID conhecido; eles permanecem fora da vitrine.

## 6. Journal e persistência

Cada lote tem um arquivo `<uuid>.jsonl`. Cada checkpoint contém lote, sequência, hash final, hash do checkpoint anterior, horário, versão, hash próprio e HMAC. Não contém dados pessoais nem saldo.

O writer:

1. Bloqueia o lote para estabilizar sua cadeia.
2. Verifica a auditoria antes de ancorar: não assina um histórico inconsistente.
3. Adquire `flock` exclusivo no arquivo, relê e valida os registros já existentes.
4. Não regrava checkpoint repetido da mesma sequência/hash e não permite voltar a uma sequência anterior.
5. Acrescenta uma linha, executa `flush`, `fsync` do arquivo e sincroniza o diretório.

Leitores usam lock compartilhado. Um append interrompido, JSON inválido, bytes de codificação inválida ou remoção de um registro intermediário resultam em falha; o código não limpa nem repara silenciosamente o journal.

Esse append-only é uma disciplina da aplicação, não armazenamento imutável/WORM imposto pelo sistema operacional.

### Docker

Volume `audit_checkpoints`:

- Worker: leitura/escrita em `/data/audit`.
- API: somente leitura em `/data/audit`.
- PostgreSQL: volume separado `pg_data`.

`AUDIT_DIR` aponta para o journal. Fora do Docker, o padrão é `backend/audit/`, ignorado pelo Git. Um journal local do host não é automaticamente o mesmo journal do volume Docker: use as ferramentas dentro do worker para inspecionar o ambiente Docker.

O código usa `fcntl` e semântica de filesystem POSIX. O caminho suportado é Linux/Docker; em Windows, use Docker/WSL. Não foi validado armazenamento de rede com semântica de locks/fsync diferente.

## 7. Worker, comandos e lotes antigos

O worker financeiro agora faz também uma passagem de checkpoints por ciclo. Percorre páginas de até 100 lotes por UUID, mantendo cursor entre ciclos e voltando ao início ao concluir. Inclui lotes vazios, abertos, fechados e cancelados. Se um lote está bloqueado, tenta novamente em uma volta seguinte.

Não existe transação única entre banco e filesystem: o lance é confirmado primeiro; o checkpoint é posterior. O intervalo ainda não ancorado fica explicitamente pendente. Não há SLA de tempo fixo para ancoragem sob carga.

No Docker, para conferir todas as páginas imediatamente:

```sh
docker compose exec worker python -m app.audit.checkpoints
```

Fora do Docker:

```sh
npm run audit:checkpoint
```

### Bootstrap de lotes anteriores à entrega 7

Novos lotes já nascem com cabeçalho assinado na mesma transação da criação. Não há autocorreção de cabeçalho ausente ao dar lance.

Lotes antigos realmente vazios podem receber um cabeçalho inicial por ação explícita:

```sh
docker compose exec worker python -m app.audit.checkpoints --init-empty-heads
```

Ou, fora do Docker:

```sh
npm run audit:init-empty
```

Essa é uma operação de preparação para dados legados conhecidos. Não a use para encobrir um incidente. Ela só trata cabeçalhos ausentes, sem liderança e sem nenhum lance; ignora cabeçalhos existentes e nunca autentica retroativamente lances sem assinatura/cabeçalho. Histórico com lances e cabeçalho perdido exige investigação e recuperação de backup confiável.

## 8. O que detecta e quais são os limites

| Situação                                                                 | Resultado esperado                                             |
| ------------------------------------------------------------------------ | -------------------------------------------------------------- |
| Alterar valor, horário, identidade pública, hash ou assinatura de lance  | Inconsistência                                                 |
| Inserir lance ou alterar sua sequência                                   | Inconsistência                                                 |
| Remover lance intermediário                                              | Inconsistência na cadeia/contagem                              |
| Remover último lance mantendo cabeçalho                                  | Inconsistência no cabeçalho/liderança                          |
| Restaurar histórico e cabeçalho antigos com journal mais novo preservado | Inconsistência com checkpoint externo                          |
| Mudança após o último checkpoint, antes da próxima ancoragem             | Proteção contra rollback desse trecho ainda pendente           |
| Apagar todo o journal                                                    | Checkpoint pendente; não afirmar ancoragem                     |
| Truncar o fim do journal e restaurar banco para o mesmo estado antigo    | Pode não ser detectado se o atacante controla ambos            |
| Comprometer `AUDIT_SECRET`                                               | Permite falsificar assinaturas; fora da garantia               |
| Administrador controla banco, volume e chaves                            | Pode reescrever/restaurar o conjunto; não há proteção absoluta |

A auditoria cobre histórico de **lances**, não autentica todo campo do banco ou todos os dados financeiros/comprovantes. Os comprovantes continuam sendo snapshots persistidos, sem assinatura própria nesta versão. A API e o código de verificação precisam ser confiáveis.

Versão de chave suportada: 1. Rotação com múltiplas versões ainda não está implementada. Não substitua a chave depois de gerar registros assinados.

## 9. Backup e recuperação

Preserve juntos: dump PostgreSQL, imagens, journal e cópia privada da chave `AUDIT_SECRET`. Guarde a chave fora do Git e controle o acesso. Para obter um backup coerente, interrompa os produtores de escrita ou use uma estratégia coordenada de snapshots; volume separado não é backup.

Restaurar somente um dump antigo mantendo journal novo deve gerar alerta de rollback. Não apague o journal para fazer o alerta desaparecer: investigue e recupere o conjunto confiável. Backups e restauração operacional de produção ainda não foram automatizados nem testados nesta entrega.

## 10. Testes de adulteração

Testes usam schemas PostgreSQL descartáveis e diretórios temporários exclusivos. Nunca adulteram os lotes demo para demonstrar a falha.

Cobertura: histórico vazio autenticado, ausência de cabeçalho, assinatura/valor/hash/sequência alterados, inserção, remoção intermediária/final, troca de UUID público, restauração de cabeçalho antigo legitimamente assinado com checkpoint novo, journal parcial/corrompido, remoção intermediária de checkpoint, storage inacessível e journal apagado tratado como pendente.

A revisão visual da barra e das imagens é separada da verificação criptográfica. Imagens de categorias são fotografias/obras CC0 do Cleveland Museum, armazenadas no frontend. Créditos individuais: `frontend/public/images/categories/credits.json`.

## Referências

- Python, fsync: https://docs.python.org/3.12/library/os.html#os.fsync
- PostgreSQL, isolamento: https://www.postgresql.org/docs/17/transaction-iso.html
- Cleveland, acervo aberto: https://www.clevelandart.org/open-access-api

## Validação executada

106 testes backend e 20 frontend aprovados, com lint, formatação, tipagem e build. Docker reconstruído com worker gravando o volume de checkpoints e API lendo em modo somente leitura. Auditorias dos lotes demo vazio e arrematado foram consultadas sem login pelo Nginx e retornaram `valid/anchored`. Todas as sete imagens locais responderam com JPEG válido. Os testes de adulteração usaram apenas schemas temporários; o banco de demonstração não foi adulterado.

Exemplo local: http://localhost:5174/lots/38339c12-eaac-4f60-8450-7e2e4ae0a132/audit . O cabeçalho ausente do lote legado conhecido vazio foi inicializado explicitamente; assinaturas de lances existentes foram preservadas. Não houve inspeção visual completa no navegador nem deploy/commit/push nesta continuação.
