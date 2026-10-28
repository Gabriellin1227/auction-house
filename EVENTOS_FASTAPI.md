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
