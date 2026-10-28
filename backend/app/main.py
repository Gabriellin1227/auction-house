from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.auctioneers.router import router as auctioneers_router
from app.auth.router import router as auth_router
from app.config import get_settings
from app.db.session import get_engine
from app.lots.router import router as lots_router
from app.users.router import router as users_router
from app.wallets.router import router as wallets_router

app = FastAPI(title="Auction House API")
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(wallets_router)
app.include_router(auctioneers_router)
app.include_router(lots_router)
get_settings().media_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    "/media",
    StaticFiles(directory=get_settings().media_dir, check_dir=False),
    name="media",
)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError):
    # Do not echo passwords/tokens or the submitted request body in errors.
    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {
                    "loc": item["loc"],
                    "msg": "Campo obrigatório"
                    if item["type"] == "missing"
                    else "Campo não permitido"
                    if item["type"] == "extra_forbidden"
                    else "Valor inválido para este campo",
                    "type": item["type"],
                }
                for item in error.errors()
            ]
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503, detail="Banco de dados indisponível"
        ) from None
    return {"status": "ready"}
