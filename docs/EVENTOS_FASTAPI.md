# Eventos em Python e FastAPI, com exemplos deste projeto

## 1. A ideia em uma frase

Uma parte do programa conta **o que aconteceu**; outras partes reagem a isso.

- Comando: “aceite meu lance de R$ 80”. Pode ser recusado.
- Evento: “o lance de R$ 80 foi aceito”. Descreve um fato confirmado.
- Produtor: quem cria esse evento, aqui o serviço de lances.
- Consumidor: quem reage, aqui a distribuição para as salas do lote.

FastAPI não transforma automaticamente uma aplicação em orientada a eventos. Ele recebe pedidos HTTP e conexões WebSocket; nós escolhemos como produzir, guardar e consumir os eventos.

## 2. Primeiro, um exemplo pequeno em Python puro

Este exemplo é **didático**, executável sozinho, sem banco e sem FastAPI:

```python
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True)
class LanceAceito:
    lote_id: str
    valor_centavos: int

class Eventos:
    def __init__(self):
        self.consumidores: list[Callable[[LanceAceito], None]] = []

    def assinar(self, consumidor):
        self.consumidores.append(consumidor)

    def publicar(self, evento):
        for consumidor in self.consumidores:
            consumidor(evento)

bus = Eventos()
bus.assinar(lambda evento: print(f"Atualizar sala: {evento.lote_id}"))
bus.assinar(lambda evento: print(f"Valor: {evento.valor_centavos} centavos"))
bus.publicar(LanceAceito("lote-1", 8000))
```

`LanceAceito` carrega os dados. `assinar` cadastra uma reação. `publicar` chama as reações cadastradas. POO continua presente nas classes; eventos são uma forma de comunicação entre elas.

Limite: se esse processo cair, nada fica salvo. Uma reação lenta também atrasa as seguintes. Por isso o exemplo não é o mecanismo de garantia financeira do leilão.

## 3. REST e eventos funcionam juntos?

Sim. Os CRUDs REST continuam com a estrutura conhecida:

```text
HTTP → rota → schema → serviço → banco → resposta HTTP
```

| Intenção       | Exemplo REST           | O que o serviço faz                                 |
| -------------- | ---------------------- | --------------------------------------------------- |
| Criar lote     | `POST /lots`           | Valida proprietário, importa item e persiste        |
| Ler lote       | `GET /lots/{id}`       | Consulta e devolve a representação                  |
| Editar lote    | `PATCH /lots/{id}`     | Confere propriedade, período e ausência de lances   |
| Cancelar lote  | `DELETE /lots/{id}`    | Cancela logicamente, preservando histórico          |
| Oferecer lance | `POST /lots/{id}/bids` | Executa uma transação de negócio, não um CRUD livre |

Em geral, HTTP usa POST para criar, GET para consultar, PATCH para alterações parciais e DELETE para remover/cancelar conforme o contrato. Isso não significa expor edição/exclusão de qualquer tabela. Lance, extrato e liquidação são históricos: o usuário não deve ter um PATCH para mudar o valor de um lance aceito.

Depois de uma operação que interessa a outras partes, adicionamos eventos:

```text
HTTP POST → serviço → transação [lance + saldo + outbox] → commit → HTTP 201
                                                       ↓
                         publicador → hub → WebSocket → telas dos clientes
```

## 4. Exemplo real: a rota recebe o comando

Trecho de `backend/app/bids/router.py`:

```python
@router.post("/{lot_id}/bids", response_model=BidAccepted, status_code=201)
def place_bid(lot_id, data, user, session):
    return BidService(session).place(lot_id, user.id, data.amount_cents)
```

O trecho omite as anotações de dependência para facilitar a leitura. No arquivo real elas validam UUID, schema, autenticação e papel de licitante.

A rota não envia WebSocket nem altera saldo por conta própria. Ela delega ao serviço.

## 5. O evento nasce na mesma transação do lance

Trecho do serviço, depois de conferir locks e regras:

```python
self.session.add(
    OutboxEvent(
        lot_id=lot_id,
        aggregate_version=lot.version,
        event_type="BidAccepted",
        payload=result.model_dump(mode="json"),
    )
)
```

E o método que coordena a operação confirma tudo:

```python
result = self._place(lot_id, user_id, amount)
self.session.commit()
return result
```

`_place` também prepara lance, reserva, liberação anterior, extrato, prazo e assinatura. Só existe um commit para o conjunto. Se falhar, faz rollback.

**Por que a outbox?** Se fizéssemos commit e depois enviássemos diretamente uma mensagem, o processo poderia cair entre as duas ações: o lance estaria salvo, mas ninguém saberia que precisava atualizar as telas. Na outbox, o lembrete de publicar já está no banco junto com o lance.

Não usamos `BackgroundTasks` como fila durável: uma tarefa em memória pode desaparecer no reinício. A durabilidade aqui vem do PostgreSQL.

## 6. O que o consumidor deve fazer

O consumidor lê eventos confirmados e tenta publicá-los. Se falha, registra tentativa e agenda nova execução. Ao reiniciar, busca pendências de novo.

O consumidor **não recalcula quem ganhou o lance** e não reserva saldo novamente. Isso já aconteceu na transação. Sua função nesta entrega é distribuir a informação confirmada.

A distribuição usa filas em memória por conexão. Um cliente lento recebe instrução de sincronização em vez de acumular uma fila ilimitada. Essas filas não substituem a outbox nem o estado persistido.

## 7. O que é o WebSocket

HTTP normal: o navegador pergunta e o servidor responde. WebSocket: mantém uma conexão aberta, pela qual o servidor pode avisar quando algo muda.

Exemplo didático independente:

```python
from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.websocket("/exemplo")
async def exemplo(socket: WebSocket):
    await socket.accept()
    await socket.send_json({"type": "Conectado"})
    await socket.close()
```

Isso mostra o transporte, não implementa outbox nem um leilão. No projeto, a rota de sala mantém a conexão e entrega eventos do lote.

Referências oficiais: [WebSockets no FastAPI](https://fastapi.tiangolo.com/advanced/websockets/), [lifespan do FastAPI](https://fastapi.tiangolo.com/advanced/events/), [SELECT e SKIP LOCKED no PostgreSQL](https://www.postgresql.org/docs/17/sql-select.html).

## 8. Consumidor real da entrega 5

Agora implementado em `backend/app/events/publisher.py`. Este trecho seleciona somente eventos confirmados e pendentes; outra transação que esteja publicando uma linha a mantém bloqueada:

```python
events = self.session.scalars(
    select(OutboxEvent)
    .where(
        OutboxEvent.published_at.is_(None),
        OutboxEvent.next_attempt_at <= now,
    )
    .order_by(OutboxEvent.created_at, OutboxEvent.id)
    .limit(50)
    .with_for_update(skip_locked=True)
).all()
```

`SKIP LOCKED` pula as linhas já tomadas por outra transação. Não é uma garantia de ordem total dos avisos; a versão e a consulta HTTP recuperam o estado do lote.

Para cada evento, o publicador incrementa `attempts`, chama a entrega e, se ela funciona, preenche `published_at`. Se falha, deixa pendente e move `next_attempt_at` com espera exponencial, até 60 segundos. As retentativas continuam enquanto estiver pendente. O publicador não altera carteiras.

O envelope distribuído tem esta forma:

```python
{
    "type": "BidAccepted",
    "event_id": "uuid-do-evento",
    "lot_id": "uuid-do-lote",
    "version": 2,
    "payload": {
        "amount_cents": 9000,
        # Demais campos públicos do aceite, incluindo prazo e licitante público.
    },
}
```

O evento avisa que houve mudança; o cliente consulta `GET /lots/{id}` para obter o estado atual, em vez de tentar reconstruir saldo ou regras financeiras pelo aviso.

## 9. Ciclo de vida e WebSocket no projeto

`backend/app/events/runtime.py` inicializa o hub e o publicador no `lifespan`:

```python
@asynccontextmanager
async def lifespan(app):
    hub = RoomHub()
    app.state.room_hub = hub
    app.state.event_engine = get_engine()
    stop = asyncio.Event()
    task = asyncio.create_task(publish_loop(app.state.event_engine, hub, stop))
    try:
        yield
    finally:
        stop.set()
        await task
```

Trecho simplificado: o arquivo real também permite desabilitar a publicação por configuração. `publish_loop` consulta a outbox a cada 0,5 segundo e executa o acesso SQL síncrono fora do event loop, com `asyncio.to_thread`. O thread pede a distribuição ao hub no event loop com `asyncio.run_coroutine_threadsafe`.

**Não confunda os nomes:** `lifespan` cuida de iniciar/parar os recursos da aplicação; `BidAccepted` é um evento de negócio.

A rota `WS /ws/lots/{id}` é pública, assim como o histórico. Ela inscreve a conexão na sala, valida existência e envia `ResyncRequired` para o navegador consultar o estado atual. Depois entrega avisos e uma solicitação de sincronização a cada 15 segundos. Comandos recebidos pelo socket são recusados: lances continuam autenticados por HTTP.

O proxy Nginx suporta Upgrade HTTP/1.1 e o proxy Vite habilita `ws: true`. No site, a URL é `/api/ws/lots/{id}`; o proxy remove `/api` antes de chegar ao FastAPI.

## 10. Reconexão e repetição

`frontend/src/hooks/useLiveLot.ts` conecta, busca estado no HTTP, reage a eventos novos e reconecta com espera crescente até 15 segundos. Um evento de versão menor/igual à atual é descartado. Se faltar uma versão, não há tentativa de inventar o que aconteceu: lê o estado atual pelo HTTP.

Uma resposta HTTP atrasada de versão menor não substitui a versão nova já recebida após um aceite. Ao reabrir a aba ou voltar a internet, também há sincronização. O heartbeat recupera alterações de período e cancelamentos que ainda não possuem evento próprio.

Publicar no hub e confirmar `published_at` não são a mesma operação atômica: uma queda entre elas pode repetir o aviso. Os consumidores precisam tolerar repetição. `published_at` significa entrega ao hub, **não confirmação de recebimento por cada navegador**. Clientes offline recuperam estado, não uma promessa de receber todos os avisos antigos.

## 11. Limites e próximos passos

- Uma instância/processo da API, com um hub em memória. Não execute múltiplos workers Uvicorn ou múltiplas réplicas: cada um teria clientes diferentes e poderia consumir eventos destinados ao outro. Para escalar, adicione um barramento compartilhado/distribuição por instância.
- Filas por conexão limitadas a 64 mensagens; excesso solicita sincronização. Limite global: 500 conexões por processo.
- Sem RabbitMQ ou Redis nesta topologia inicial. O PostgreSQL fornece a outbox durável; o hub só distribui aos clientes atualmente conectados.
- A entrega 6 acrescentou worker financeiro, liquidação e comprovante; consulte [WORKER_LIQUIDACAO_COMPROVANTES.md](WORKER_LIQUIDACAO_COMPROVANTES.md). Auditoria pública completa e deploy continuam pendentes.
- `EVENTS_ENABLED=false` desabilita somente a publicação automática, para manutenção/testes; o lance continua gravando eventos pendentes.

Esta entrega não usa event sourcing: as tabelas de negócio guardam o estado atual. A outbox comunica as mudanças; não é a única fonte usada para reconstruir o sistema.

## 12. Como conferir esta entrega

1. `npm run setup:env` e `npm run docker:up`.
2. Abra um lote em dois navegadores; entre com os dois clientes demo e tenha saldo disponível.
3. Dê um lance no primeiro. No segundo, preço, liderança, prazo e histórico devem se atualizar sem recarregar a página.
4. Supere a oferta no segundo: no primeiro aparece que foi superado e a reserva é liberada no backend. A carteira será consultada novamente ao abrir Minha conta.
5. Interrompa a conexão e reconecte: a sala deve buscar o estado atual, inclusive lances feitos durante a desconexão.
6. Ao voltar a uma aba, a sala também sincroniza. O botão Atualizar lote continua disponível para conferência manual.

Resultado: 77 testes backend e 13 frontend aprovados; lint, formatação, TypeScript e build aprovados. Docker saudável. WebSocket real validado na API direta e no Nginx com Upgrade e `ResyncRequired`. Os testes de duas conexões exercitam o aceite e a publicação com PostgreSQL real. Não houve inspeção visual em navegador nesta sessão. Entrega 5 local, sem novo commit/push; os commits anteriores `fda1e78` e `9814237` já estão na main remota.
