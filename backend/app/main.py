from fastapi import FastAPI

app = FastAPI(title="Auction House API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
